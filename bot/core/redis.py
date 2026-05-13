"""Настройки Redis."""

import redis.asyncio as redis
from contextlib import asynccontextmanager

from bot.core.config import config


_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Получение асинхронного Redis-клиента."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
        )
    return _redis_client


@asynccontextmanager
async def redis_lock(key: str, ttl_seconds: int = 5):
    """Простая Redis-блокировка через SET NX EX."""
    redis_client = get_redis_client()
    acquired = await redis_client.set(key, "1", ex=ttl_seconds, nx=True)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            await redis_client.delete(key)
