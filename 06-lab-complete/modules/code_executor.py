"""
Code Executor — Runs generated Python code in a sandboxed subprocess.
Validates code safety, captures output, and handles errors with retry logic.
"""

import os
import sys
import time
import uuid
import subprocess
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import config


@dataclass
class ExecutionResult:
    """Result of a code execution."""
    status: str  # "success", "error", "timeout"
    execution_time_ms: int = 0
    output_files: list = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    error: str = None

    def to_dict(self):
        return asdict(self)


class CodeExecutor:
    """Executes Python code in a sandboxed subprocess."""

    def __init__(self):
        self.output_dir = config.OUTPUT_DIR
        self.timeout = config.EXECUTION_TIMEOUT

    def execute(self, script: str, data_path: str = None, output_filename: str = None) -> ExecutionResult:
        """
        Execute a Python script string in a subprocess.

        Args:
            script: Python code string to execute
            data_path: Path to the CSV data file
            output_filename: Custom output filename (default: auto-generated)
        """
        # Step 1: Extract Python from an LLM response, then validate it.
        script = self._extract_python_code(script)
        safety_check = self._validate_code(script)
        if safety_check:
            return ExecutionResult(
                status="error",
                error=f"Code safety violation: {safety_check}",
            )

        # Step 2: Prepare output path
        if not output_filename:
            output_filename = f"chart_{uuid.uuid4().hex[:8]}.png"
        output_path = str(self.output_dir / output_filename)

        # Step 3: Inject data path and output path into script
        prepared_script = self._prepare_script(script, data_path, output_path)

        # Step 4: Write script to temp file
        temp_script_path = str(self.output_dir / f"_temp_script_{uuid.uuid4().hex[:6]}.py")
        with open(temp_script_path, "w", encoding="utf-8") as f:
            f.write(prepared_script)

        # Step 5: Execute
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.output_dir),
                env=self._get_safe_env(),
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Collect output files
            output_files = []
            if os.path.exists(output_path):
                output_files.append({
                    "type": "image/png",
                    "path": output_path,
                    "filename": output_filename,
                    "size_bytes": os.path.getsize(output_path),
                })

            # Also check for any HTML files (plotly)
            html_path = output_path.replace(".png", ".html")
            if os.path.exists(html_path):
                output_files.append({
                    "type": "text/html",
                    "path": html_path,
                    "filename": output_filename.replace(".png", ".html"),
                    "size_bytes": os.path.getsize(html_path),
                })

            if result.returncode == 0 and output_files:
                return ExecutionResult(
                    status="success",
                    execution_time_ms=elapsed_ms,
                    output_files=output_files,
                    stdout=result.stdout[:5000],  # Limit output size
                    stderr=result.stderr[:2000],
                )
            elif result.returncode == 0:
                return ExecutionResult(
                    status="error",
                    execution_time_ms=elapsed_ms,
                    stdout=result.stdout[:5000],
                    stderr=result.stderr[:2000],
                    error="Code ran successfully but did not create a chart image.",
                )
            else:
                return ExecutionResult(
                    status="error",
                    execution_time_ms=elapsed_ms,
                    output_files=output_files,
                    stdout=result.stdout[:5000],
                    stderr=result.stderr[:5000],
                    error=self._parse_error(result.stderr),
                )

        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                status="timeout",
                execution_time_ms=elapsed_ms,
                error=f"Code execution timed out after {self.timeout} seconds",
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                error=f"Execution error: {str(e)}",
            )
        finally:
            # Clean up temp script
            try:
                if os.path.exists(temp_script_path):
                    os.remove(temp_script_path)
            except Exception:
                pass

    def _validate_code(self, script: str) -> str:
        """
        Check code for dangerous patterns.
        Returns error message if unsafe, empty string if safe.
        """
        for pattern in config.BLOCKED_PATTERNS:
            # Allow os.path but block os.system
            if pattern == "os.system" and "os.system" in script:
                return f"Blocked pattern found: {pattern}"
            elif pattern == "open(" and "open(" in script:
                # Allow open() only for reading the data file
                # Count occurrences — allow 1 for data loading
                opens = [m.start() for m in re.finditer(r'\bopen\s*\(', script)]
                if len(opens) > 2:
                    return f"Too many file open operations"
            elif pattern not in ("os.system", "open(", "pathlib"):
                if pattern in script:
                    return f"Blocked pattern found: {pattern}"

        return ""

    def _prepare_script(self, script: str, data_path: str, output_path: str) -> str:
        """Inject data path, output path, and non-interactive backend into script."""
        data_path_normalized = data_path.replace("\\", "/") if data_path else ""
        output_path_normalized = output_path.replace("\\", "/")

        # Force non-interactive matplotlib backend and define path variables in preamble
        preamble = (
            "import matplotlib\n"
            "matplotlib.use('Agg')  # Non-interactive backend\n"
            "import warnings\n"
            "warnings.filterwarnings('ignore')\n\n"
        )
        if data_path_normalized:
            preamble += f"DATA_FILE_PATH = \"{data_path_normalized}\"\n"
        preamble += f"OUTPUT_FILE_PATH = \"{output_path_normalized}\"\n\n"

        # Replace placeholder data path
        if data_path_normalized:
            # Replace assignments like DATA_FILE_PATH = ... to avoid syntax errors
            script = re.sub(r'\bDATA_FILE_PATH\s*=\s*[^#\n]+', f'DATA_FILE_PATH = "{data_path_normalized}"', script)
            script = script.replace('"DATA_FILE_PATH"', f'"{data_path_normalized}"')
            script = script.replace("'DATA_FILE_PATH'", f'"{data_path_normalized}"')
            script = script.replace("data.csv", data_path_normalized)
            script = script.replace('"data_path"', f'"{data_path_normalized}"')
            # LLMs often copy the original upload filename into read_csv().
            script = re.sub(
                r"pd\.read_csv\(\s*(['\"])(.*?)\1\s*\)",
                "pd.read_csv(DATA_FILE_PATH)",
                script,
            )

        # Replace placeholder output path
        script = re.sub(r'\bOUTPUT_FILE_PATH\s*=\s*[^#\n]+', f'OUTPUT_FILE_PATH = "{output_path_normalized}"', script)
        script = script.replace('"OUTPUT_FILE_PATH"', f'"{output_path_normalized}"')
        script = script.replace("'OUTPUT_FILE_PATH'", f'"{output_path_normalized}"')
        script = script.replace("output_chart.png", output_path_normalized)
        script = script.replace('"output_path"', f'"{output_path_normalized}"')

        # Replace interactive display with a server-side image.
        script = re.sub(
            r"plt\.show\s*\([^)]*\)",
            "# plt.show() disabled for non-interactive execution",
            script,
        )
        if "plt." in script and "savefig(" not in script:
            script += (
                "\n\nplt.tight_layout()\n"
                "plt.savefig(OUTPUT_FILE_PATH, dpi=150, bbox_inches='tight', facecolor='white')\n"
                "plt.close('all')\n"
            )

        return preamble + script

    def _extract_python_code(self, text: str) -> str:
        """Extract executable Python from markdown or a narrative LLM response."""
        text = (text or "").strip()
        fenced = re.findall(
            r"`{2,3}\s*(?:python|py)?\s*\n(.*?)`{1,3}",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fenced:
            return max(fenced, key=len).strip()

        # Some model responses omit the opening fence but still include a code section.
        code_start = re.search(r"(?m)^(?:import|from)\s+\w+", text)
        if code_start:
            return text[code_start.start():].strip().rstrip("`").strip()
        return text

    def _get_safe_env(self) -> dict:
        """Create a restricted environment for subprocess."""
        env = os.environ.copy()
        # Set matplotlib to non-interactive
        env["MPLBACKEND"] = "Agg"
        return env

    def _parse_error(self, stderr: str) -> str:
        """Extract the most relevant error message from stderr."""
        lines = stderr.strip().split("\n")
        # Get the last few lines which usually contain the actual error
        error_lines = []
        for line in reversed(lines):
            error_lines.insert(0, line)
            if line.startswith(("Traceback", "Error", "Exception")) or len(error_lines) >= 5:
                break
        return "\n".join(error_lines[-5:])
