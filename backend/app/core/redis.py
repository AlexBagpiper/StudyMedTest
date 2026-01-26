import json
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import settings

# Global redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create a redis client
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


async def set_json(key: str, value: Any, expire: int = 86400):
    """
    Store a dict as JSON in redis
    """
    client = await get_redis_client()
    await client.set(key, json.dumps(value), ex=expire)


async def get_json(key: str) -> Optional[Any]:
    """
    Get a dict from JSON in redis
    """
    client = await get_redis_client()
    data = await client.get(key)
    if data:
        return json.loads(data)
    return None


async def delete_key(key: str):
    """
    Delete a key from redis
    """
    client = await get_redis_client()
    await client.delete(key)
