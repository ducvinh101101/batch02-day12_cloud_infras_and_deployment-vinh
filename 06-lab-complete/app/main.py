"""Production wrapper for the Medical Research AI Agent."""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import config
from agents.orchestrator import AgentResponse, OrchestratorAgent
from app.auth import verify_api_key
from app.cost_guard import check_and_record_cost, get_budget_usage
from app.rate_limiter import check_rate_limit
from app.storage import redis_client
from modules.input_layer import MedicalCSVParser
from modules.memory import MemoryModule

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }, ensure_ascii=False)


logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())
logger = logging.getLogger("medical-agent")
START_TIME = time.time()
INSTANCE_ID = f"medical-{uuid.uuid4().hex[:8]}"
agent = None
is_ready = False


class DemoMedicalAgent:
    """Useful local demo when a Gemini key has not been configured."""

    def __init__(self):
        self.parser = MedicalCSVParser()
        self.memory = MemoryModule()

    def upload_dataset(self, session_id: str, file_path: str) -> dict:
        session_id = self.memory.get_or_create_session(session_id)
        schema = self.parser.parse(file_path)
        self.memory.update_active_dataset(
            session_id, file_path, json.dumps(schema.to_dict(), ensure_ascii=False)
        )
        return schema.to_dict()

    async def process_request(self, prompt: str, session_id: str) -> AgentResponse:
        session_id = self.memory.get_or_create_session(session_id)
        context = self.memory.get_current_context(session_id)
        dataset = context.get("active_dataset")
        if dataset:
            schema = dataset.get("schema", {})
            text = (
                f"Demo mode: dataset có {schema.get('row_count', '?')} hàng và "
                f"{schema.get('col_count', '?')} cột. Đã nhận yêu cầu: {prompt}. "
                "Cấu hình GEMINI_API_KEY để tạo phân tích và biểu đồ bằng AI."
            )
        else:
            text = (
                "Agent đang chạy ở demo mode. Hãy upload CSV mẫu để xem nhận diện "
                "schema, hoặc cấu hình GEMINI_API_KEY để dùng đầy đủ AI."
            )
        self.memory.save_conversation_turn(session_id, "user", prompt)
        self.memory.save_conversation_turn(session_id, "assistant", text)
        return AgentResponse(text=text)


def session_id(request: Request) -> str:
    requested = request.headers.get("X-Session-ID")
    return agent.memory.get_or_create_session(requested)


def protected_user(request: Request, user_id: str = Depends(verify_api_key)) -> str:
    check_rate_limit(user_id)
    request.state.user_id = user_id
    return user_id


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global agent, is_ready
    redis_client.ping()
    if config.GEMINI_API_KEY:
        agent = OrchestratorAgent()
    elif config.DEMO_MODE:
        agent = DemoMedicalAgent()
    else:
        raise RuntimeError("GEMINI_API_KEY is required when DEMO_MODE=false")
    is_ready = True
    logger.info("startup instance=%s demo_mode=%s", INSTANCE_ID, isinstance(agent, DemoMedicalAgent))
    yield
    is_ready = False
    redis_client.close()


app = FastAPI(title="Medical Research AI Agent", version="2.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Instance-ID"] = INSTANCE_ID
    response.headers["X-Content-Type-Options"] = "nosniff"
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.1f instance=%s",
        request.method, request.url.path, response.status_code,
        (time.perf_counter() - started) * 1000, INSTANCE_ID,
    )
    return response


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse((config.STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
@app.get("/api/health")
async def health(request: Request):
    sid = session_id(request) if agent else None
    return {
        "status": "ok",
        "agent_ready": agent is not None,
        "session_id": sid,
        "model": config.GEMINI_MODEL if config.GEMINI_API_KEY else "demo-mode",
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
    }


@app.get("/ready")
async def ready():
    if not is_ready:
        raise HTTPException(503, "Agent is not ready")
    try:
        redis_client.ping()
    except Exception as exc:
        raise HTTPException(503, "Redis is not ready") from exc
    return {"status": "ready", "instance_id": INSTANCE_ID}


@app.post("/api/upload")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(protected_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")
    contents = await file.read()
    if len(contents) > config.MAX_FILE_SIZE_BYTES:
        raise HTTPException(400, f"Maximum file size is {config.MAX_FILE_SIZE_MB}MB")
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename.replace('/', '_').replace(chr(92), '_')}"
    file_path = config.UPLOAD_DIR / safe_name
    await run_in_threadpool(file_path.write_bytes, contents)
    sid = session_id(request)
    schema = await run_in_threadpool(agent.upload_dataset, sid, str(file_path))
    check_and_record_cost(user_id, 10, 10)
    return {
        "success": True,
        "session_id": sid,
        "response": {
            "text": f"Đã tải lên `{file.filename}`: {schema['row_count']} hàng, {schema['col_count']} cột.",
            "schema": schema,
        },
    }


@app.post("/api/chat")
async def chat(request: Request, user_id: str = Depends(protected_user)):
    body = await request.json()
    prompt = str(body.get("message", "")).strip()
    if not prompt:
        raise HTTPException(400, "Message cannot be empty")
    sid = session_id(request)
    response = await agent.process_request(prompt=prompt, session_id=sid)
    usage = check_and_record_cost(user_id, len(prompt.split()) * 2, len(response.text.split()) * 2)
    return {"success": True, "session_id": sid, "budget": usage, "response": response.to_dict()}


@app.get("/api/chart/{filename}")
async def get_chart(filename: str):
    path = config.OUTPUT_DIR / filename
    if not path.exists() or path.name != filename:
        raise HTTPException(404, "Chart not found")
    return FileResponse(path, media_type="image/png" if filename.endswith(".png") else "text/html")


@app.get("/api/history")
async def get_history(request: Request, _user_id: str = Depends(verify_api_key)):
    sid = session_id(request)
    charts = agent.memory.get_chart_history(sid, last_n=20)
    return {
        "session_id": sid,
        "charts": [
            {
                "chart_id": chart["chart_id"],
                "iteration": chart["iteration"],
                "chart_type": chart["chart_config"].get("chart_type", "unknown"),
                "title": chart["chart_config"].get("title", ""),
                "image_path": chart.get("image_path", ""),
                "created_at": chart["created_at"],
            }
            for chart in charts
        ],
    }


@app.delete("/api/session")
async def reset_session(request: Request, _user_id: str = Depends(verify_api_key)):
    sid = session_id(request)
    agent.memory.clear_session(sid)
    return {"success": True, "new_session_id": agent.memory.create_session()}


@app.get("/api/code/{chart_id}")
async def get_code(chart_id: str, _user_id: str = Depends(verify_api_key)):
    chart = agent.memory.get_chart_by_id(chart_id)
    if not chart:
        raise HTTPException(404, "Chart not found")
    return {"chart_id": chart_id, "code": chart.get("code", ""), "chart_config": chart.get("chart_config", {})}


@app.get("/api/budget")
async def budget(user_id: str = Depends(verify_api_key)):
    return get_budget_usage(user_id)
