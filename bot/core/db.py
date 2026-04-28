"""SQLAlchemy настройки для работы с базой данных."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.core.config import config


class Base(DeclarativeBase):
    """Базовый класс SQLAlchemy моделей."""


engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение асинхронной сессии для работы с базой данных."""
    async with async_session_factory() as session:
        yield session
