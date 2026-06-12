"""Redis-backed monthly LLM budget guard."""
import time

from fastapi import HTTPException

from app.config import settings
from app.storage import redis_client

INPUT_PRICE_PER_1K = 0.00015
OUTPUT_PRICE_PER_1K = 0.0006


def _key(user_id: str) -> str:
    return f"budget:{user_id}:{time.strftime('%Y-%m')}"


def get_budget_usage(user_id: str) -> dict:
    used = float(redis_client.get(_key(user_id)) or 0)
    return {
        "used_usd": round(used, 6),
        "limit_usd": settings.monthly_budget_usd,
        "remaining_usd": round(max(0, settings.monthly_budget_usd - used), 6),
    }


def check_and_record_cost(user_id: str, input_tokens: int, output_tokens: int) -> dict:
    cost = input_tokens / 1000 * INPUT_PRICE_PER_1K
    cost += output_tokens / 1000 * OUTPUT_PRICE_PER_1K
    key = _key(user_id)
    current = float(redis_client.get(key) or 0)
    if current + cost > settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="Monthly budget exceeded")
    pipe = redis_client.pipeline()
    pipe.incrbyfloat(key, cost)
    pipe.expire(key, 32 * 24 * 3600)
    new_total, _ = pipe.execute()
    return {
        "request_cost_usd": round(cost, 6),
        "used_usd": round(float(new_total), 6),
        "limit_usd": settings.monthly_budget_usd,
    }

