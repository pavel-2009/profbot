"""Настройки Redis."""

import redis.asyncio as redis

from bot.core.config import config


def get_redis_client() -> redis.Redis:
    """Получение асинхронного Redis-клиента."""
    return redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        decode_responses=True,
    )
