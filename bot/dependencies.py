"""Зависимости для бота."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.db import async_session_factory
from bot.services.user_service import UserService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение асинхронной сессии в стиле DI."""
    async with async_session_factory() as session:
        yield session


def get_user_service(session: AsyncSession) -> UserService:
    """Получение сервиса для работы с пользователями."""
    return UserService(session)
