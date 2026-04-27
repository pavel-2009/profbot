"""Настройки Redis."""

from redis import Redis

from bot.core.config import config


def get_redis() -> Redis:
    """Получение клиента Redis."""
    return Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
    )
