import json
from typing import Any, Optional
from app.db.db import redis_client

def cache_set(key: str, value: Any, ttl: int | None = None):
    data = json.dumps(value, ensure_ascii=False, default=str)
    redis_client.set(key, data, ex=ttl)

def cache_get(key: str) -> Optional[Any]:
    raw = redis_client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None

def cache_delete(key: str):
    redis_client.delete(key)