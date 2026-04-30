"""Роутер статистики и рейтинга."""

from collections import defaultdict
from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.core.db import async_session_factory
from bot.dependencies import get_user_service
from bot.repositories.transaction_repository import TransactionRepository
from bot.repositories.user_repository import UserRepository

router = Router()


def statistics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📈 График за 30 дней", callback_data="stats_graph_30d")]]
    )


@router.message(Command("rating"))
@router.message(F.text == "🏆 Рейтинг")
async def rating(message: types.Message) -> None:
    async with async_session_factory() as session:
        repo = UserRepository(session)
        top_users = await repo.get_top_users_by_balance(limit=10)
        my_rank = await repo.get_user_rank_by_balance(message.from_user.id)

    if not top_users:
        await message.answer("Рейтинг пока пуст.")
        return

    lines = ["🏆 ТОП-10 ПО БАЛАНСУ"]
    for index, user in enumerate(top_users, start=1):
        lines.append(f"{index}. {user.first_name} (@{user.username}) — {user.balance} 🔮")
    lines.append("")
    lines.append(f"Ваше место: {my_rank if my_rank else '—'}")
    await message.answer("\n".join(lines))


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
@router.callback_query(F.data == "view_stats")
async def user_statistics(event: types.Message | types.CallbackQuery) -> None:
    user_id = event.from_user.id
    async with async_session_factory() as session:
        user_service = get_user_service(session)
        profile = await user_service.get_user_profile(user_id)
        repo = TransactionRepository(session)
        all_transactions = await repo.get_transactions_by_user_id(user_id)

    if profile is None:
        text = "Пользователь не найден. Зарегистрируйтесь через /start."
        if isinstance(event, types.CallbackQuery):
            await event.message.answer(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    days_in_bot = max((datetime.utcnow() - datetime.strptime(profile.registration_date, "%Y-%m-%d")).days, 0)
    earned_total = sum(max(t.amount, 0) for t in all_transactions)
    spent_total = sum(abs(min(t.amount, 0)) for t in all_transactions)
    conversion = int((profile.stats.active_invited_users / profile.stats.invited_users) * 100) if profile.stats.invited_users else 0
    most_common_reason = all_transactions[0].reason if all_transactions else "—"

    text = (
        "📊 ВАША СТАТИСТИКА\n\n"
        "Активность:\n"
        f"- Дней в боте: {days_in_bot}\n"
        f"- Заходов всего: {profile.stats.active_sessions}\n"
        f"- Команд выполнено: {profile.stats.commands_executed}\n\n"
        "Экономика:\n"
        f"- Баланс: {profile.balance} 🔮\n"
        f"- Заработано всего: {earned_total} 🔮\n"
        f"- Потрачено: {spent_total} 🔮\n\n"
        "Рефералы:\n"
        f"- Приглашено: {profile.stats.invited_users}\n"
        f"- Активных: {profile.stats.active_invited_users} (за 7 дней)\n"
        f"- Конверсия: {conversion}%\n\n"
        "Магазин:\n"
        f"- Покупок: {profile.stats.transactions}\n"
        f"- Потрачено: {profile.stats.spent_crystals} 🔮\n"
        f"- Чаще всего: {most_common_reason}"
    )

    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, reply_markup=statistics_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=statistics_keyboard())


@router.callback_query(F.data == "stats_graph_30d")
async def statistics_graph(callback: types.CallbackQuery) -> None:
    async with async_session_factory() as session:
        repo = TransactionRepository(session)
        transactions = await repo.get_transactions_by_user_for_days(callback.from_user.id, days=30)

    if not transactions:
        await callback.message.answer("За последние 30 дней транзакций нет.")
        await callback.answer()
        return

    daily = defaultdict(int)
    for tx in transactions:
        daily[tx.created_at.strftime("%m-%d")] += tx.amount

    lines = ["📈 График прибыли/убыли за 30 дней:"]
    for day, amount in sorted(daily.items()):
        bar = "🟩" * min(abs(amount) // 10 + 1, 10)
        sign = "+" if amount >= 0 else "-"
        icon = "📈" if amount >= 0 else "📉"
        lines.append(f"{day}: {icon} {sign}{abs(amount)} {bar}")

    await callback.message.answer("\n".join(lines))
    await callback.answer()
