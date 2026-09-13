import hashlib
import json
import redis

from core.config import settings

type JSONValue = str | int | float | bool | None | dict[str, JSONValue] | list[JSONValue]

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

def make_cache_key(image_id: int, payload: dict[str, JSONValue]) -> str:
    normalized = json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f'transform:{image_id}:{digest}'

def get_cached(key: str) -> dict[str, JSONValue] | None:
    raw = redis_client.get(key)
    if raw is None:
        return None
    data: dict[str, JSONValue] = json.loads(raw)
    return data

def set_cached(key: str, value: dict[str, JSONValue], ttl_seconds: int = 3600) -> None:
    redis_client.set(key, json.dumps(value), ex=ttl_seconds)