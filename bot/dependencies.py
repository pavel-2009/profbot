"""Зависимости для бота."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.db import async_session_factory
from bot.services.user_service import UserService
from bot.services.shop_service import ShopService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение асинхронной сессии в стиле DI."""
    async with async_session_factory() as session:
        yield session


def get_user_service(session: AsyncSession) -> UserService:
    """Получение сервиса для работы с пользователями."""
    return UserService(session)

def get_shop_service(session: AsyncSession) -> ShopService:
    """Получение сервиса для работы с магазином."""
    return ShopService(session)
