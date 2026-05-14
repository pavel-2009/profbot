"""Роутер для получения списка заказов и управления ими (для администраторов)."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.core.db import async_session_factory
from bot.core.redis import redis_lock
from bot.dependencies import get_shop_service
from bot.middlewares.admin import AdminMiddleware
from bot.models.order import Order

router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


def _orders_keyboard(open_orders: list[Order], show_all: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=str(i), callback_data=f"show_order_{order.id}") for i, order in enumerate(open_orders[:5], start=1)]]
    if not show_all and len(open_orders) > 5:
        rows.append([InlineKeyboardButton(text="Показать все", callback_data="show_all_orders")])
    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_orders")])
    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Завершить", callback_data=f"complete_{order_id}")],
            [InlineKeyboardButton(text="⬅️ Назад к заказам", callback_data="refresh_orders")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu")],
        ]
    )


async def _render_open_orders(target_message: Message, show_all: bool = False) -> None:
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        open_orders = await shop_service.get_all_open_orders()

    if not open_orders:
        await target_message.answer("Нет открытых заказов.")
        return

    orders_to_show = open_orders if show_all else open_orders[:5]
    response = "Открытые заказы:\n\n" + "\n".join(
        f"ID: {order.id}, User ID: {order.user_id}, Product ID: {order.product_id}, Status: {order.status.value}"
        for order in orders_to_show
    )
    await target_message.answer(response, reply_markup=_orders_keyboard(open_orders, show_all=show_all))


@router.message(Command("orders"))
@router.message(F.text == "📦 Заказы")
async def get_open_orders(message: Message) -> None:
    await _render_open_orders(message)


@router.callback_query(F.data == "show_all_orders")
async def show_all_orders(callback_query: CallbackQuery) -> None:
    await _render_open_orders(callback_query.message, show_all=True)
    await callback_query.answer()


@router.callback_query(F.data == "refresh_orders")
async def refresh_orders(callback_query: CallbackQuery) -> None:
    await _render_open_orders(callback_query.message)
    await callback_query.answer("Обновлено")


@router.callback_query(F.data == "admin_menu")
async def admin_menu_back(callback_query: CallbackQuery) -> None:
    await callback_query.message.answer("Вернул в админ-меню. Используйте кнопки ниже.")
    await callback_query.answer()


@router.callback_query(F.data.startswith("show_order_"))
async def show_order_details(callback_query: CallbackQuery) -> None:
    order_id = int(callback_query.data.split("_")[-1])
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        order = await shop_service.get_order_by_id(order_id)

    if not order:
        await callback_query.message.answer("Заказ не найден.")
        await callback_query.answer()
        return

    response = (
        "Детали заказа:\n"
        f"ID: {order.id}\n"
        f"User ID: {order.user_id}\n"
        f"Product ID: {order.product_id}\n"
        f"Status: {order.status.value}"
    )
    await callback_query.message.answer(response, reply_markup=_order_keyboard(order.id))
    await callback_query.answer()


@router.callback_query(F.data.startswith("complete_"))
async def complete_order(callback_query: CallbackQuery) -> None:
    order_id = int(callback_query.data.split("_")[-1])
    async with redis_lock(f"admin:complete_order:{callback_query.from_user.id}:{order_id}") as acquired:
        if not acquired:
            await callback_query.answer("⏳ Заказ уже обрабатывается")
            return

        async with async_session_factory() as session:
            shop_service = get_shop_service(session)
            success = await shop_service.complete_order(order_id)

    if not success:
        await callback_query.message.answer("Не удалось завершить заказ: заказ не найден.")
    else:
        await callback_query.message.answer(f"Заказ {order_id} завершен.")
    await callback_query.answer()
