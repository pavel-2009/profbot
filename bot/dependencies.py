"""Зависимости для бота."""

from sqlalchemy.ext.asyncio import AsyncSession
from bot.services.user_service import UserService
from bot.core.db import get_async_session


async def get_user_service(session: AsyncSession) -> UserService:
    """Получение сервиса для работы с пользователями."""
    return UserService(session)
