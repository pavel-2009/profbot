"""Роутер для стартового сообщения."""

from aiogram import Router, types
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.user_service import UserService
from bot.dependencies import get_user_service
from bot.core.db import get_async_session


router = Router()


@router.message(CommandStart())    
async def start(message: types.Message) -> None:
    """Обработчик команды /start."""
    
    try:
        async for session in get_async_session():
            user_service: UserService = await get_user_service(session)
            
            if await user_service.user_exists(message.from_user.id):
                await message.answer("Вы уже зарегистрированы!")
                return
            
            telegram_id = message.from_user.id
            username = message.from_user.username or f"user_{telegram_id}"
            first_name = message.from_user.first_name or "Пользователь"
            last_name = message.from_user.last_name or "Пользователь"
            
            await user_service.register_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                invited_by=None
            )
            await message.answer(f"""👋 Добро пожаловать, {first_name}!\n\n
Ты автоматически зарегистрирован в системе "ProfBot"\n.
Твой ID в системе: {telegram_id}\n\n

🎁 Тебе начислено 100 кристаллов за регистрацию!\n\n

Используй /help, чтобы увидеть список команд.""")

    except Exception as e:
        print(f"Error occurred while handling /start command: {e}")
        await message.answer("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")