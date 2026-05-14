"""Роутер для стартовой команды админов."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.core.db import async_session_factory
from bot.dependencies import get_shop_service
from bot.keyboards.keyboards import admin_menu_keyboard
from bot.middlewares.admin import AdminMiddleware

router = Router()
router.message.middleware(AdminMiddleware())


@router.message(Command("admin"))
async def admin_start(message: Message):
    await message.answer("Добро пожаловать в административное меню!", reply_markup=admin_menu_keyboard)


@router.message(Command("admin_stats"))
@router.message(F.text == "📊 Общая статистика")
async def admin_global_stats(message: Message):
    """Показать общую статистику по боту для админов."""
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        stats = await shop_service.get_admin_global_stats()

    text = (
        "📊 <b>Общая статистика проекта</b>\n\n"
        "👥 <b>Пользователи</b>\n"
        f"• Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"• Суммарный баланс: <b>{stats['total_balance']}</b>\n\n"
        "🛒 <b>Магазин</b>\n"
        f"• Всего товаров: <b>{stats['total_products']}</b>\n"
        f"• AUTO-товаров: <b>{stats['auto_products']}</b>\n"
        f"• MANUAL-товаров: <b>{stats['manual_products']}</b>\n\n"
        "📦 <b>Заказы</b>\n"
        f"• Всего заказов: <b>{stats['total_orders']}</b>\n"
        f"• Открытых заказов: <b>{stats['open_orders']}</b>\n\n"
        "💸 <b>Экономика</b>\n"
        f"• Транзакций: <b>{stats['total_transactions']}</b>\n"
        f"• Оборот (|сумма|): <b>{stats['economy_turnover']}</b>"
    )
    await message.answer(text, parse_mode="HTML")
