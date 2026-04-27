"""Настройки Redis."""

from redis import Redis


def get_redis() -> Redis:
    """Получение клиента Redis."""
    return Redis(host='localhost', port=6379, db=0)
