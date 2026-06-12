"""
Agent production-ready — dùng trong Docker production stack.
"""
import os
import time
import logging
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from utils.mock_llm import ask

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "time": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if isinstance(record.msg, dict):
            payload.update(record.msg)
            payload.pop("message")
        return json.dumps(payload)


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())

START_TIME = time.time()
is_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_ready
    logger.info("Starting agent...")
    await asyncio.sleep(0.1)  # simulate init
    is_ready = True
    logger.info("Agent ready")
    yield
    is_ready = False
    logger.info("Agent shutdown")


app = FastAPI(title="Agent (Docker Advanced)", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


@app.get("/")
def root():
    return {
        "app": "AI Agent",
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.post("/ask")
async def ask_agent(payload: AskRequest):
    question = payload.question
    logger.info({"event": "request", "question_length": len(question)})
    return {"answer": await run_in_threadpool(ask, question)}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ready")
def ready():
    if not is_ready:
        raise HTTPException(503, "not ready")
    return {"ready": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
