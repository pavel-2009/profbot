"""Базовые фикстуры для тестов."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.core.db import Base
from bot.models import order, product, statistics, transaction, user  # noqa: F401
from bot.repositories import user_repository


@pytest_asyncio.fixture(scope="function", autouse=True)
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Replace global Redis client with test client."""
    # Сохраняем оригинальный клиент
    original_client = getattr(user_repository, 'redis_client', None)
    
    # Создаем НОВЫЙ клиент для тестов
    test_client = Redis(
        host='localhost',
        port=6379,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=False,
    )
    
    try:
        await test_client.ping()
    except RedisError as error:
        await test_client.aclose()  # Используем aclose() вместо close()
        pytest.skip(f"Redis is not available: {error}")
    
    # Подменяем клиент в репозитории
    user_repository.redis_client = test_client
    
    # Очищаем тестовые ключи
    await test_client.delete("user_lock:1", "user_lock:2", "user_lock:3")
    
    yield test_client
    
    # Возвращаем оригинальный клиент
    if original_client is not None:
        user_repository.redis_client = original_client
    else:
        delattr(user_repository, 'redis_client')
    
    # Очищаем и закрываем тестовый клиент
    await test_client.delete("user_lock:1", "user_lock:2", "user_lock:3")
    await test_client.aclose()  # Используем aclose() вместо close()


@pytest_asyncio.fixture()
async def session_factory(
    tmp_path: Path,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Create SQLite session factory for tests."""
    database_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Create SQLite session for one test."""
    async with session_factory() as opened_session:
        yield opened_session