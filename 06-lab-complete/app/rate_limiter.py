"""Atomic Redis sliding-window rate limiter."""
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.storage import redis_client

RATE_LIMIT_SCRIPT = redis_client.register_script("""
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1] - 60)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[3]) then
  return -1
end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[2])
redis.call('EXPIRE', KEYS[1], 60)
return tonumber(ARGV[3]) - count - 1
""")


def check_rate_limit(user_id: str) -> None:
    now = time.time()
    remaining = RATE_LIMIT_SCRIPT(
        keys=[f"rate:{user_id}"],
        args=[now, f"{now}:{uuid.uuid4().hex}", settings.rate_limit_per_minute],
    )
    if int(remaining) < 0:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} requests/minute",
            headers={"Retry-After": "60"},
        )
