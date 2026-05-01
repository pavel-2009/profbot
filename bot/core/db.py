"""SQLAlchemy настройки для работы с базой данных."""

import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import OperationalError

from bot.core.config import config


class Base(DeclarativeBase):
    """Базовый класс SQLAlchemy моделей."""


engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    connect_args={"timeout": 30, "check_same_thread": False}
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение асинхронной сессии для работы с базой данных."""
    async with async_session_factory() as session:
        yield session


async def execute_with_retry(coro, max_retries: int = 3, delay: float = 0.5):
    """Выполнить операцию с retry при ошибке database locked."""
    for attempt in range(max_retries):
        try:
            return await coro
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                continue
            raise
