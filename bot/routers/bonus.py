"""Роутер для управления бонусами пользователей."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.dependencies import get_user_service
from bot.services.user_service import UserService
from bot.core.db import async_session_factory


router = Router()


@router.message(F.text == "🎁 Бонус")
@router.message(Command("daily"))
async def daily_bonus(message: Message) -> None:
    """Обработчик команды /daily для получения ежедневного бонуса."""
    
    async with async_session_factory() as session:
        user_service: UserService = get_user_service(session)
        result = await user_service.apply_daily_bonus(message.from_user.id)
    
    await message.answer(result["answer"])
    
