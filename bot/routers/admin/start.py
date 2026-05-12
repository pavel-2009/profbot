"""Роутер для стартовой команды админов."""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import func, select

from bot.core.db import async_session_factory
from bot.keyboards.keyboards import admin_menu_keyboard
from bot.middlewares.admin import AdminMiddleware
from bot.models.order import Order, OrderStatus
from bot.models.product import Product, DeliveryType
from bot.models.transaction import Transaction
from bot.models.user import User


router = Router()
router.message.middleware(AdminMiddleware())


@router.message(Command("admin"))
async def admin_start(message: Message):
    await message.answer("Добро пожаловать в административное меню!", reply_markup=admin_menu_keyboard)


@router.message(Command("admin_stats"))
@router.message(lambda msg: msg.text == "📊 Общая статистика")
async def admin_global_stats(message: Message):
    """Показать общую статистику по боту для админов."""
    async with async_session_factory() as session:
        total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        total_balance = (await session.execute(select(func.coalesce(func.sum(User.balance), 0)))).scalar_one()

        total_products = (await session.execute(select(func.count()).select_from(Product))).scalar_one()
        auto_products = (await session.execute(select(func.count()).where(Product.delivery_type == DeliveryType.AUTO))).scalar_one()
        manual_products = (await session.execute(select(func.count()).where(Product.delivery_type == DeliveryType.MANUAL))).scalar_one()

        total_orders = (await session.execute(select(func.count()).select_from(Order))).scalar_one()
        open_orders = (await session.execute(select(func.count()).where(Order.status == OrderStatus.OPEN))).scalar_one()

        total_transactions = (await session.execute(select(func.count()).select_from(Transaction))).scalar_one()
        economy_turnover = (await session.execute(select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0)))).scalar_one()

    text = (
        "📊 <b>Общая статистика проекта</b>\n\n"
        "👥 <b>Пользователи</b>\n"
        f"• Всего пользователей: <b>{total_users}</b>\n"
        f"• Суммарный баланс: <b>{total_balance}</b>\n\n"
        "🛒 <b>Магазин</b>\n"
        f"• Всего товаров: <b>{total_products}</b>\n"
        f"• AUTO-товаров: <b>{auto_products}</b>\n"
        f"• MANUAL-товаров: <b>{manual_products}</b>\n\n"
        "📦 <b>Заказы</b>\n"
        f"• Всего заказов: <b>{total_orders}</b>\n"
        f"• Открытых заказов: <b>{open_orders}</b>\n\n"
        "💸 <b>Экономика</b>\n"
        f"• Транзакций: <b>{total_transactions}</b>\n"
        f"• Оборот (|сумма|): <b>{economy_turnover}</b>"
    )
    await message.answer(text, parse_mode="HTML")
