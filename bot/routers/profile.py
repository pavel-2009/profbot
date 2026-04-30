"""Роутер для управления профилем пользователя."""

import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from bot.core.db import async_session_factory
from bot.dependencies import get_user_service
from bot.keyboards.keyboards import profile_keyboard
from bot.services.user_service import UserService
from bot.repositories.statistics_repository import StatisticsRepository

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "👤 Профиль")
@router.message(Command("profile"))
async def user_profile(message: types.Message) -> None:
    """Обработчик команды /profile."""
    logger.info(f"User {message.from_user.id} requested profile")

    try:
        async with async_session_factory() as session:
            user_service: UserService = get_user_service(session)
            await StatisticsRepository(session).increment_fields(message.from_user.id, active_sessions=1, commands_executed=1)
            user = await user_service.get_user_by_telegram_id(message.from_user.id)

            if user is None:
                logger.warning(f"User {message.from_user.id} not found in database")
                await message.answer("Пользователь не найден. Зарегистрируйтесь через /start.")
                return

            profile = await user_service.get_user_profile(message.from_user.id)
            if profile is None:
                logger.warning(f"Failed to load profile for user {message.from_user.id}")
                await message.answer("Не удалось загрузить профиль. Попробуйте позже.")
                return

            transactions_text = "\n".join(
                f"• {item.date}: {item.amount:+} — {item.description}" for item in profile.transactions[:5]
            ) or "Транзакций пока нет."

            profile_text = (
                "👤 Профиль\n"
                f"ID: {profile.telegram_id}\n"
                f"Имя: {profile.name}\n"
                f"Username: {profile.username}\n"
                f"Дата регистрации: {profile.registration_date}\n"
                f"Баланс: 🔮 {profile.balance} кристаллов\n\n"
                "📊 Статистика:\n"
                f"- Приглашено друзей: {profile.stats.invited_users}\n"
                f"- Заработано по рефералке: {profile.stats.earned_crystals_via_referrals} кристаллов\n"
                f"- Потрачено: {profile.stats.spent_crystals} кристаллов\n"
                f"- Транзакций: {profile.stats.transactions}\n\n"
                "🎁 Реферальная ссылка:\n"
                f"{profile.referral_link}\n\n"
                "📋 История транзакций:\n"
                f"{transactions_text}"
            )

            await message.answer(profile_text, reply_markup=profile_keyboard)
            logger.info(f"Profile sent to user {message.from_user.id}")
    except Exception as error:
        logger.error(f"Error handling profile command for user {message.from_user.id}: {error}", exc_info=True)
        await message.answer("Произошла ошибка при загрузке профиля. Пожалуйста, попробуйте позже.")
