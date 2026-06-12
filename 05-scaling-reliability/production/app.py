"""Stateless agent: all conversation state is stored in Redis."""
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from utils.mock_llm import ask

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
START_TIME = time.time()
INSTANCE_ID = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")
is_ready = False


def append_to_history(session_id: str, role: str, content: str) -> None:
    key = f"session:{session_id}"
    message = json.dumps({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    pipe = redis_client.pipeline()
    pipe.rpush(key, message)
    pipe.ltrim(key, -20, -1)
    pipe.expire(key, SESSION_TTL_SECONDS)
    pipe.execute()


def load_history(session_id: str) -> list[dict]:
    return [json.loads(item) for item in redis_client.lrange(f"session:{session_id}", 0, -1)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global is_ready
    await run_in_threadpool(redis_client.ping)
    is_ready = True
    logger.info("Starting %s with Redis storage", INSTANCE_ID)
    yield
    is_ready = False
    logger.info("Shutting down %s", INSTANCE_ID)
    redis_client.close()


app = FastAPI(title="Stateless Agent", version="4.0.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


@app.post("/chat")
async def chat(body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    await run_in_threadpool(append_to_history, session_id, "user", body.question)
    answer = await run_in_threadpool(ask, body.question)
    await run_in_threadpool(append_to_history, session_id, "assistant", answer)
    history = await run_in_threadpool(load_history, session_id)
    return {
        "session_id": session_id,
        "question": body.question,
        "answer": answer,
        "turn": sum(item["role"] == "user" for item in history),
        "served_by": INSTANCE_ID,
        "storage": "redis",
    }


@app.get("/chat/{session_id}/history")
async def get_history(session_id: str):
    history = await run_in_threadpool(load_history, session_id)
    if not history:
        raise HTTPException(404, "Session not found or expired")
    return {"session_id": session_id, "messages": history, "count": len(history)}


@app.delete("/chat/{session_id}")
async def delete_session(session_id: str):
    await run_in_threadpool(redis_client.delete, f"session:{session_id}")
    return {"deleted": session_id}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "storage": "redis",
    }


@app.get("/ready")
def ready():
    if not is_ready:
        raise HTTPException(503, "Agent not ready")
    try:
        redis_client.ping()
    except Exception as exc:
        raise HTTPException(503, "Redis not available") from exc
    return {"ready": True, "instance": INSTANCE_ID}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        timeout_graceful_shutdown=30,
    )
