"""
Orchestrator Agent — Central LLM-powered agent that coordinates all modules.
Uses Google Gemini API with function calling to analyze data, generate charts,
and provide medical insights.
"""

import json
import traceback
from typing import Optional
from dataclasses import dataclass, field, asdict

from google import genai
from google.genai import types

import config
from agents.prompts import SYSTEM_PROMPT, INSIGHT_PROMPT, CODE_PATCH_PROMPT, ERROR_FIX_PROMPT
from agents.intent_classifier import classify_intent, UserIntent
from modules.input_layer import MedicalCSVParser
from modules.data_analysis import StatisticalAnalyzer, MedicalDomainClassifier
from modules.visualization_engine import VisualizationDecisionEngine
from modules.code_generator import PythonCodeGenerator
from modules.code_executor import CodeExecutor
from modules.memory import MemoryModule


@dataclass
class AgentResponse:
    """Structured response from the Orchestrator."""
    text: str = ""
    chart_path: str = None
    chart_id: str = None
    code: str = None
    insights: str = None
    chart_config: dict = None
    schema: dict = None
    stats_report: dict = None
    error: str = None

    def to_dict(self):
        d = asdict(self)
        # Remove None values
        return {k: v for k, v in d.items() if v is not None}


class OrchestratorAgent:
    """
    Central orchestrator that coordinates data analysis, visualization,
    and insight generation using Gemini LLM.
    """

    def __init__(self):
        # Initialize Gemini client
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set. Please configure in .env file.")
        
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = config.GEMINI_MODEL

        # Initialize modules
        self.parser = MedicalCSVParser()
        self.analyzer = StatisticalAnalyzer()
        self.viz_engine = VisualizationDecisionEngine()
        self.code_gen = PythonCodeGenerator()
        self.executor = CodeExecutor()
        self.memory = MemoryModule()

    def upload_dataset(self, session_id: str, file_path: str) -> dict:
        """Parse CSV, save to memory as active dataset, and return schema."""
        session_id = self.memory.get_or_create_session(session_id)
        schema = self.parser.parse(file_path)
        self.memory.update_active_dataset(session_id, file_path, json.dumps(schema.to_dict(), ensure_ascii=False))
        return schema.to_dict()

    # ── Main Entry Point ────────────────────────────────────────
    async def process_request(self, prompt: str, session_id: str, file_path: str = None) -> AgentResponse:
        """
        Process a user request — the main entry point.

        Args:
            prompt: User's message text
            session_id: Current session ID
            file_path: Path to uploaded CSV file (if any)
        """
        try:
            # Ensure session exists
            session_id = self.memory.get_or_create_session(session_id)

            # Save user message to memory
            self.memory.save_conversation_turn(session_id, "user", prompt)

            # Get current context
            context = self.memory.get_current_context(session_id)
            has_active_dataset = context["active_dataset"] is not None
            has_active_chart = context["current_chart"] is not None

            # If a new file is uploaded, process it first
            if file_path:
                response = await self._handle_new_file(prompt, session_id, file_path)
            else:
                # Classify intent
                intent = classify_intent(prompt, has_active_chart, has_active_dataset)

                if intent == UserIntent.ANALYZE_NEW:
                    response = AgentResponse(
                        text="Vui lòng upload file CSV để tôi phân tích. Bạn có thể kéo thả file vào khu vực upload hoặc click để chọn file."
                    )
                elif intent == UserIntent.CREATE_CHART:
                    response = await self._handle_create_chart(prompt, session_id, context)
                elif intent == UserIntent.MODIFY_CHART:
                    response = await self._handle_modify_chart(prompt, session_id, context)
                elif intent == UserIntent.EXPLAIN_INSIGHT:
                    response = await self._handle_explain(prompt, session_id, context)
                elif intent == UserIntent.EXPORT:
                    response = await self._handle_export(prompt, session_id, context)
                else:
                    response = await self._handle_general(prompt, session_id, context)

            # Save agent response to memory
            self.memory.save_conversation_turn(
                session_id, "assistant", response.text,
                metadata={"chart_id": response.chart_id} if response.chart_id else None
            )

            return response

        except Exception as e:
            error_msg = f"Đã xảy ra lỗi: {str(e)}"
            if config.DEBUG:
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return AgentResponse(text=error_msg, error=str(e))

    # ── Handle New File Upload ──────────────────────────────────

    async def _handle_new_file(self, prompt: str, session_id: str, file_path: str) -> AgentResponse:
        """Process a newly uploaded CSV file."""
        # Parse CSV
        schema = self.parser.parse(file_path)
        
        # Load DataFrame and compute statistics
        df = self.parser.load_dataframe(file_path, schema.encoding, schema.delimiter)
        stats_report = self.analyzer.analyze(df, schema.columns)

        # Save to memory
        self.memory.update_active_dataset(session_id, file_path, json.dumps(schema.to_dict(), ensure_ascii=False))

        # Generate description using LLM
        schema_text = schema.summary_text()
        stats_text = stats_report.summary_text()
        medical_ctx = stats_report.medical_context

        llm_prompt = f"""Người dùng vừa upload file CSV. Hãy mô tả tổng quan dataset và đề xuất phân tích.

{schema_text}

Loại nghiên cứu phát hiện: {medical_ctx.get('study_type', 'Unknown')}
Phân tích đề xuất: {', '.join(medical_ctx.get('suggested_analyses', []))}

Tin nhắn của người dùng: "{prompt}"

Hãy:
1. Mô tả tổng quan dataset (số hàng, cột, loại dữ liệu chính từ cột và ví dụ)
2. Phân loại loại nghiên cứu
3. Đề xuất 2-3 biểu đồ/phân tích phù hợp nhất
4. Nếu người dùng đã yêu cầu cụ thể, xác nhận bạn sẽ thực hiện"""

        llm_response = await self._call_llm(llm_prompt)

        # If user also asked for a specific chart, create it
        if prompt and len(prompt.strip()) > 10:
            # Try to create a chart based on the prompt
            chart_response = await self._create_chart_from_prompt(prompt, session_id, schema, df, file_path)
            if chart_response.chart_path:
                chart_response.text = llm_response + "\n\n---\n\n" + chart_response.text
                chart_response.schema = schema.to_dict()
                chart_response.stats_report = asdict(stats_report)
                return chart_response

        return AgentResponse(
            text=llm_response,
            schema=schema.to_dict(),
            stats_report=asdict(stats_report),
        )

    # ── Handle Chart Creation ───────────────────────────────────

    async def _handle_create_chart(self, prompt: str, session_id: str, context: dict) -> AgentResponse:
        """Create a new visualization based on user prompt."""
        dataset = context.get("active_dataset")
        if not dataset:
            return AgentResponse(
                text="Chưa có dataset nào được tải lên. Vui lòng upload file CSV trước khi yêu cầu tạo biểu đồ."
            )

        schema = dataset["schema"]
        file_path = dataset["path"]
        df = self.parser.load_dataframe(file_path, schema.get("encoding", "utf-8"), schema.get("delimiter", ","))

        return await self._create_chart_from_prompt(prompt, session_id, schema, df, file_path)

    async def _create_chart_from_prompt(self, prompt: str, session_id: str, 
                                         schema, df, file_path: str) -> AgentResponse:
        """Internal method to create a chart from a prompt."""
        # Handle both DataSchema object and dict
        if hasattr(schema, 'columns'):
            schema_columns = schema.columns
            schema_dict = schema.to_dict()
        else:
            schema_columns = schema.get("columns", [])
            schema_dict = schema

        # Step 1: Decide chart type
        chart_config = self.viz_engine.decide(prompt, schema_columns)
        chart_config_dict = chart_config.to_dict()

        # Step 2: Use LLM to refine chart config and generate better code
        llm_code = await self._generate_code_with_llm(prompt, chart_config_dict, schema_columns, file_path)
        
        if llm_code:
            code = llm_code
        else:
            # Fallback to template-based generation
            code = self.code_gen.generate(chart_config_dict, schema_columns, file_path)

        # Step 3: Execute code
        exec_result = self.executor.execute(code, file_path)

        # Step 4: Handle errors with retry
        retry_count = 0
        while exec_result.status != "success" and retry_count < 3:
            retry_count += 1
            fixed_code = await self._fix_code_with_llm(
                code, exec_result.error or exec_result.stderr,
                [c["name"] for c in schema_columns]
            )
            if fixed_code:
                code = fixed_code
                exec_result = self.executor.execute(code, file_path)
            else:
                break

        if exec_result.status != "success":
            return AgentResponse(
                text=f"❌ Không thể tạo biểu đồ sau {retry_count + 1} lần thử.\n\n"
                     f"Lỗi: {exec_result.error or exec_result.stderr}\n\n"
                     f"Bạn có thể thử mô tả yêu cầu khác hoặc upload lại dữ liệu.",
                code=code,
                error=exec_result.error,
            )

        # Step 5: Get chart image path
        chart_path = None
        chart_filename = None
        if exec_result.output_files:
            chart_path = exec_result.output_files[0]["path"]
            chart_filename = exec_result.output_files[0]["filename"]

        # Step 6: Generate insights
        insights = await self._generate_insights(chart_config_dict, exec_result.stdout)

        # Step 7: Save to memory
        chart_id = self.memory.save_chart(
            session_id, chart_config_dict, code,
            chart_path or "", insights
        )

        # Step 8: Build response text
        chart_type_name = chart_config_dict.get("chart_type", "").replace("_", " ").title()
        response_text = f"📊 **{chart_type_name}**: {chart_config_dict.get('title', '')}\n\n{insights}"

        return AgentResponse(
            text=response_text,
            chart_path=chart_filename,
            chart_id=chart_id,
            code=code,
            insights=insights,
            chart_config=chart_config_dict,
        )

    # ── Handle Chart Modification ───────────────────────────────

    async def _handle_modify_chart(self, prompt: str, session_id: str, context: dict) -> AgentResponse:
        """Modify the current chart based on user request."""
        current_chart = context.get("current_chart")
        if not current_chart:
            return AgentResponse(text="Chưa có biểu đồ nào để chỉnh sửa. Hãy tạo biểu đồ trước.")

        dataset = context.get("active_dataset")
        if not dataset:
            return AgentResponse(text="Không tìm thấy dataset. Vui lòng upload lại.")

        current_code = current_chart.get("code", "")
        file_path = dataset["path"]

        # Use LLM to patch code
        patched_code = await self._patch_code_with_llm(current_code, prompt)
        if not patched_code:
            return AgentResponse(text="Không thể hiểu yêu cầu chỉnh sửa. Vui lòng mô tả chi tiết hơn.")

        # Execute patched code
        exec_result = self.executor.execute(patched_code, file_path)

        # Retry on failure
        if exec_result.status != "success":
            fixed_code = await self._fix_code_with_llm(
                patched_code, exec_result.error or exec_result.stderr,
                []  # We don't need column names for patching
            )
            if fixed_code:
                exec_result = self.executor.execute(fixed_code, file_path)
                if exec_result.status == "success":
                    patched_code = fixed_code

        if exec_result.status != "success":
            return AgentResponse(
                text=f"❌ Không thể áp dụng chỉnh sửa.\nLỗi: {exec_result.error}",
                code=patched_code,
                error=exec_result.error,
            )

        # Get output
        chart_path = None
        chart_filename = None
        if exec_result.output_files:
            chart_path = exec_result.output_files[0]["path"]
            chart_filename = exec_result.output_files[0]["filename"]

        # Save updated chart
        chart_config = current_chart.get("chart_config", {})
        chart_id = self.memory.save_chart(
            session_id, chart_config, patched_code,
            chart_path or "", f"Chỉnh sửa: {prompt}"
        )

        return AgentResponse(
            text=f"✅ Đã cập nhật biểu đồ theo yêu cầu: \"{prompt}\"",
            chart_path=chart_filename,
            chart_id=chart_id,
            code=patched_code,
            chart_config=chart_config,
        )

    # ── Handle Explanation ──────────────────────────────────────

    async def _handle_explain(self, prompt: str, session_id: str, context: dict) -> AgentResponse:
        """Explain data or current chart."""
        context_text = self.memory.get_context_text(session_id)
        
        current_chart = context.get("current_chart")
        chart_info = ""
        if current_chart:
            chart_info = f"\nBiểu đồ hiện tại: {current_chart.get('chart_config', {}).get('chart_type', 'unknown')}"
            chart_info += f"\nInsights trước đó: {current_chart.get('insights', 'N/A')}"

        llm_prompt = f"""{context_text}
{chart_info}

Người dùng hỏi: "{prompt}"

Hãy giải thích chi tiết bằng tiếng Việt, sử dụng thuật ngữ y khoa khi cần."""

        response_text = await self._call_llm(llm_prompt)
        return AgentResponse(text=response_text)

    # ── Handle Export ───────────────────────────────────────────

    async def _handle_export(self, prompt: str, session_id: str, context: dict) -> AgentResponse:
        """Handle export/download requests."""
        current_chart = context.get("current_chart")
        if not current_chart:
            return AgentResponse(text="Chưa có biểu đồ nào để xuất. Hãy tạo biểu đồ trước.")

        code = current_chart.get("code", "")
        chart_path = current_chart.get("image_path", "")

        text = "📥 **Xuất dữ liệu:**\n\n"
        if chart_path:
            text += f"🖼️ Biểu đồ đã được lưu tại server. Bạn có thể tải về bằng nút Download bên dưới.\n\n"
        if code:
            text += f"💻 **Code Python:**\n```python\n{code}\n```\n"

        return AgentResponse(text=text, code=code, chart_path=current_chart.get("image_path"))

    # ── Handle General Questions ────────────────────────────────

    async def _handle_general(self, prompt: str, session_id: str, context: dict) -> AgentResponse:
        """Handle general questions about data or capabilities."""
        context_text = self.memory.get_context_text(session_id)
        llm_prompt = f"""{context_text}

Người dùng: "{prompt}"

Trả lời câu hỏi bằng tiếng Việt. Nếu liên quan đến dữ liệu, sử dụng context ở trên."""

        response_text = await self._call_llm(llm_prompt)
        return AgentResponse(text=response_text)

    # ── LLM Helper Methods ──────────────────────────────────────

    async def _call_llm(self, prompt: str) -> str:
        """Call Gemini LLM and return text response."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
            return response.text or "Không có phản hồi từ AI."
        except Exception as e:
            return f"Lỗi khi gọi AI: {str(e)}"

    async def _generate_code_with_llm(self, prompt: str, chart_config: dict,
                                        schema_columns: list, data_path: str) -> Optional[str]:
        """Use LLM to generate better visualization code."""
        columns_desc = "\n".join([
            f"- {c['name']} ({c['dtype']}, role: {c['medical_role']})"
            for c in schema_columns
        ])

        llm_prompt = f"""Sinh code Python hoàn chỉnh để tạo biểu đồ y khoa.

Yêu cầu người dùng: "{prompt}"

Cấu hình biểu đồ:
- Loại: {chart_config.get('chart_type')}
- Trục X: {chart_config.get('x_axis', 'auto')}
- Trục Y: {chart_config.get('y_axis', 'auto')}
- Nhóm (hue): {chart_config.get('hue', 'none')}
- Palette: {chart_config.get('color_palette')}
- Title: {chart_config.get('title')}

Cột dữ liệu:
{columns_desc}

Đường dẫn file CSV: sử dụng biến DATA_FILE_PATH
Đường dẫn output: sử dụng biến OUTPUT_FILE_PATH

Yêu cầu code:
1. Import đầy đủ: pandas, numpy, matplotlib, seaborn, scipy.stats
2. Dùng plt.style.use('seaborn-v0_8-whitegrid')
3. Dùng colorblind-safe palette
4. Thêm statistical annotations (p-value, sample size) nếu phù hợp
5. Thêm mean/median lines nếu histogram
6. Vietnamese labels nếu phù hợp
7. plt.savefig(OUTPUT_FILE_PATH, dpi=150, bbox_inches='tight')
8. Không dùng plt.show()
9. print() các thống kê quan trọng ở cuối

CHỈ trả về code Python thuần, KHÔNG dùng markdown, KHÔNG dùng ```python```."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=llm_prompt,
                config=types.GenerateContentConfig(
                    system_instruction="Bạn là chuyên gia Python data visualization cho nghiên cứu y khoa. Chỉ trả về code Python thuần, không markdown.",
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )
            code = response.text or ""
            # Clean up any markdown formatting
            code = self._clean_code(code)
            return code if len(code) > 50 else None
        except Exception as e:
            print(f"LLM code generation failed: {e}")
            return None

    async def _generate_insights(self, chart_config: dict, stdout: str) -> str:
        """Generate clinical insights from chart results."""
        prompt = INSIGHT_PROMPT.format(
            chart_type=chart_config.get("chart_type", "unknown"),
            x_axis=chart_config.get("x_axis", "N/A"),
            y_axis=chart_config.get("y_axis", "N/A"),
            execution_stdout=stdout or "No output captured",
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=1024,
                ),
            )
            return response.text or "Không thể tạo nhận xét."
        except Exception as e:
            return f"Không thể tạo nhận xét: {str(e)}"

    async def _patch_code_with_llm(self, current_code: str, edit_request: str) -> Optional[str]:
        """Use LLM to patch existing code based on edit request."""
        prompt = CODE_PATCH_PROMPT.format(
            current_code=current_code,
            edit_request=edit_request,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="Bạn là chuyên gia sửa code Python. Chỉ trả về code Python thuần, không markdown.",
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            code = self._clean_code(response.text or "")
            return code if len(code) > 50 else None
        except Exception as e:
            print(f"LLM code patching failed: {e}")
            return None

    async def _fix_code_with_llm(self, original_code: str, error_msg: str, column_names: list) -> Optional[str]:
        """Use LLM to fix a code error."""
        prompt = ERROR_FIX_PROMPT.format(
            original_code=original_code,
            error_message=error_msg,
            column_names=", ".join(column_names) if column_names else "unknown",
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="Bạn là chuyên gia debug Python. Sửa lỗi và trả về code Python thuần hoàn chỉnh, không markdown.",
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            code = self._clean_code(response.text or "")
            return code if len(code) > 50 else None
        except Exception as e:
            print(f"LLM error fix failed: {e}")
            return None

    def _clean_code(self, code: str) -> str:
        """Remove markdown formatting from LLM-generated code."""
        # Remove ```python ... ``` wrapper
        code = code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        elif code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()
        return code
