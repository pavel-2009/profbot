"""Роутер для управления профилем пользователя."""

import logging
from aiogram import Router, types, F
from aiogram.filters import Command

from bot.services.user_service import UserService
from bot.dependencies import get_user_service
from bot.core.db import get_async_session
from bot.keyboards.keyboards import profile_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "👤 Профиль")
@router.message(Command("profile"))
async def user_profile(message: types.Message) -> None:
    """Обработчик команды /profile."""
    
    logger.info(f"User {message.from_user.id} requested profile")
    
    try:
        async for session in get_async_session():
            try:
                user_service: UserService = await get_user_service(session)
                user = await user_service.get_user_by_telegram_id(message.from_user.id)
                
                if user is None:
                    logger.warning(f"User {message.from_user.id} not found in database")
                    await message.answer("Пользователь не найден. Пожалуйста, зарегистрируйтесь с помощью /start.")
                    return
                
                user_profile = await user_service.get_user_profile(message.from_user.id)
                if user_profile is None:
                    logger.warning(f"Failed to load profile for user {message.from_user.id}")
                    await message.answer("Не удалось загрузить профиль. Пожалуйста, попробуйте позже.")
                    return
                
                profile_text = f"""👤 ПРОФИЛЬ
        ID: {user_profile['telegram_id']}
        Имя: {user_profile['name']}
        Username: {user_profile['username']}
        Дата регистрации: {user_profile['registration_date']}
        Баланс: 🔮 {user_profile['balance']} кристаллов

        📊 СТАТИСТИКА:
        - Приглашено друзей: {user_profile['stats']['invited_users']}
        - Заработано по рефералке: {user_profile['stats']['earned_crystals_via_referrals']} кристаллов
        - Потрачено: {user_profile['stats']['spent_crystals']} кристаллов
        - Транзакций: {user_profile['stats']['transactions']}

        🎁 Реферальная ссылка:
        {user_profile['referral_link']}

        📋 История транзакций (последние 5):
        {user_profile['transactions']} """
                
                await message.answer(
                    profile_text,
                    reply_markup=profile_keyboard
                )
                logger.info(f"Profile sent to user {message.from_user.id}")
                
            except Exception as e:
                logger.error(f"Error fetching user profile for {message.from_user.id}: {e}", exc_info=True)
                await message.answer("Произошла ошибка при загрузке профиля. Пожалуйста, попробуйте позже.")
                raise
                
    except Exception as e:
        logger.error(f"Error handling profile command for user {message.from_user.id}: {e}", exc_info=True)
        try:
            await message.answer("Произошла ошибка при загрузке профиля. Пожалуйста, попробуйте позже.")
        except Exception as msg_error:
            logger.error(f"Failed to send error message: {msg_error}")