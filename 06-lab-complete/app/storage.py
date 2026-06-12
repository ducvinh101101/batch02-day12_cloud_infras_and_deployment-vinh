"""Shared Redis state with an explicit single-replica demo fallback."""
import json
import time
from collections import defaultdict
from datetime import datetime, timezone

import redis

from app.config import settings


class MemoryPipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def incrbyfloat(self, key, value):
        self.commands.append(("incrbyfloat", key, value))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", key, seconds))
        return self

    def rpush(self, key, value):
        self.commands.append(("rpush", key, value))
        return self

    def ltrim(self, key, start, end):
        self.commands.append(("ltrim", key, start, end))
        return self

    def execute(self):
        return [getattr(self.client, name)(*args) for name, *args in self.commands]


class MemoryRedis:
    """Small compatibility layer for Railway demos without a Redis service."""

    def __init__(self):
        self.values = {}
        self.lists = defaultdict(list)
        self.windows = defaultdict(list)

    def ping(self):
        return True

    def close(self):
        return None

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)
        self.lists.pop(key, None)
        self.windows.pop(key, None)

    def incrbyfloat(self, key, value):
        self.values[key] = float(self.values.get(key, 0)) + float(value)
        return self.values[key]

    def expire(self, _key, _seconds):
        return True

    def rpush(self, key, value):
        self.lists[key].append(value)
        return len(self.lists[key])

    def ltrim(self, key, start, end):
        values = self.lists[key]
        self.lists[key] = values[start:] if end == -1 else values[start:end + 1]
        return True

    def lrange(self, key, start, end):
        values = self.lists[key]
        return values[start:] if end == -1 else values[start:end + 1]

    def pipeline(self):
        return MemoryPipeline(self)

    def register_script(self, _script):
        def rate_limit(*, keys, args):
            key = keys[0]
            now = float(args[0])
            limit = int(args[2])
            self.windows[key] = [stamp for stamp in self.windows[key] if stamp > now - 60]
            if len(self.windows[key]) >= limit:
                return -1
            self.windows[key].append(now)
            return limit - len(self.windows[key])
        return rate_limit


redis_client = (
    MemoryRedis()
    if settings.redis_url == "memory://"
    else redis.Redis.from_url(settings.redis_url, decode_responses=True)
)


def append_history(session_id: str, role: str, content: str) -> None:
    key = f"session:{session_id}"
    message = json.dumps({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    pipe = redis_client.pipeline()
    pipe.rpush(key, message)
    pipe.ltrim(key, -20, -1)
    pipe.expire(key, settings.session_ttl_seconds)
    pipe.execute()


def get_history(session_id: str) -> list[dict]:
    return [json.loads(item) for item in redis_client.lrange(f"session:{session_id}", 0, -1)]


def delete_history(session_id: str) -> None:
    redis_client.delete(f"session:{session_id}")
