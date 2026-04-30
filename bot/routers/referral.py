"""Роутер для получения реферальной ссылки."""

from aiogram import Router, types, F
from aiogram.filters import Command

from bot.dependencies import get_user_service
from bot.services.user_service import UserService


router = Router()


@router.message(Command("referral"))
@router.message(F.text == "🔗 Реферальная ссылка")
async def referral_handler(message: types.Message):
    user_service: UserService = get_user_service()
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы в системе.")
        return

    referral_link = await user_service.get_user_referral(user.telegram_id)
    
    user_stats = await user_service.get_user_profile(user.telegram_id)
    invited_count = user_stats.stats.invited_users
    earned_crystals = user_stats.stats.earned_crystals_via_referrals
    
    invited_users = await user_service.get_invited_users(user.telegram_id)
    
    await message.answer(f"""🔗 ВАША РЕФЕРАЛЬНАЯ ССЫЛКА:\n
{referral_link}\n\n

За каждого приглашённого друга вы получите 🔮 50 кристаллов.\n
Друг также получит 🔮 50 кристаллов при регистрации.\n\n

Приглашено: {invited_count} человека\n
Заработано: {earned_crystals} кристаллов\n\n

Список приглашённых:
{'\n✅ '.join(user.username for user in invited_users) if invited_users else 'Пока нет приглашённых.'}""")