"""Роутер для получения реферальной ссылки."""

from aiogram import F, Router, types
from aiogram.filters import Command

from bot.core.db import async_session_factory
from bot.dependencies import get_user_service
from bot.repositories.statistics_repository import StatisticsRepository
from bot.services.user_service import UserService

router = Router()


@router.message(Command("referral"))
@router.message(F.text == "🔗 Реферальная ссылка")
async def referral_handler(message: types.Message) -> None:
    async with async_session_factory() as session:
        user_service: UserService = get_user_service(session)
        await StatisticsRepository(session).increment_fields(message.from_user.id, active_sessions=1, commands_executed=1)
        await session.commit()

        user = await user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Вы не зарегистрированы в системе.")
            return

        referral_link = await user_service.get_user_referral(user.telegram_id)
        user_stats = await user_service.get_user_profile(user.telegram_id)
        invited_count = user_stats.stats.invited_users if user_stats else 0
        earned_crystals = user_stats.stats.earned_crystals_via_referrals if user_stats else 0
        active_invited = user_stats.stats.active_invited_users if user_stats else 0
        conversion = int((active_invited / invited_count) * 100) if invited_count else 0

        await message.answer(
            f"🔗 ВАША РЕФЕРАЛЬНАЯ ССЫЛКА:\n\n{referral_link}\n\n"
            "За каждого приглашённого друга вы получите 🔮 50 кристаллов.\n"
            "Друг также получит 🔮 50 кристаллов при регистрации.\n\n"
            f"Приглашено: {invited_count}\n"
            f"Активных приглашённых: {active_invited}\n"
            f"Конверсия: {conversion}%\n"
            f"Заработано: {earned_crystals} кристаллов"
        )
