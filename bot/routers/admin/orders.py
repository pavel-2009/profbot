"""Роутер для получения списка заказов и управления ими (для администраторов)"""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from bot.middlewares.admin import AdminMiddleware
from bot.dependencies import get_shop_service
from bot.core.db import async_session_factory
from bot.models.order import Order


router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


def _get_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления заказом."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Завершить", callback_data=f"complete_{order_id}")
        ]
    ])
    return keyboard


@router.message(Command("orders"))
@router.message(F.text == "📦 Заказы")
async def get_open_orders(message: Message) -> None:
    """Обрабатывает команду /orders и отправляет администратору список открытых заказов."""
    
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        open_orders: list[Order] = await shop_service.get_all_open_orders()
    
    if not open_orders:
        await message.answer("Нет открытых заказов.")
        return
    
    response = "Открытые заказы:\n\n"
    for order in open_orders[:5]:  # Показываем только первые 5 заказов
        response += f"ID: {order.id}, User ID: {order.user_id}, Product ID: {order.product_id}, Status: {order.status.value}\n"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=str(i), callback_data=f"show_order_{order.id}") for i, order in enumerate(open_orders[:5], start=1)
        ],
        [
            InlineKeyboardButton(text="Показать все", callback_data="show_all_orders")
        ]
    ])
    
    await message.answer(response, reply_markup=keyboard)
    
    
@router.callback_query(F.data == "show_all_orders")
async def show_all_orders(callback_query: CallbackQuery) -> None:
    """Обрабатывает нажатие кнопки "Показать все"."""
    
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        open_orders: list[Order] = await shop_service.get_all_open_orders()
    
    if not open_orders:
        await callback_query.message.answer("Нет открытых заказов.")
        return
    
    response = "Открытые заказы:\n\n"
    for order in open_orders:
        response += f"ID: {order.id}, User ID: {order.user_id}, Product ID: {order.product_id}, Status: {order.status.value}\n"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=str(i), callback_data=f"show_order_{order.id}") for i, order in enumerate(open_orders[:5], start=1)
        ]
    ])
    
    await callback_query.message.answer(response, reply_markup=keyboard)
    
    
@router.callback_query(F.data.startswith("show_order_"))
async def show_order_details(callback_query: CallbackQuery) -> None:
    """Обрабатывает нажатие кнопки с ID заказа и показывает его детали."""
    
    order_id = int(callback_query.data.split("_")[-1])
    
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        open_orders: list[Order] = await shop_service.get_all_open_orders()
    
    order = next((o for o in open_orders if o.id == order_id), None)
    
    if not order:
        await callback_query.message.answer("Заказ не найден.")
        return
    
    response = f"Детали заказа:\nID: {order.id}\nUser ID: {order.user_id}\nProduct ID: {order.product_id}\nStatus: {order.status.value}"
    
    keyboard = _get_order_keyboard(order.id)
    
    await callback_query.message.answer(response, reply_markup=keyboard) 


@router.callback_query(F.data.startswith("complete_"))
async def complete_order(callback_query: CallbackQuery) -> None:
    """Обрабатывает нажатие кнопки "Завершить" и завершает заказ."""
    
    order_id = int(callback_query.data.split("_")[-1])
    
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        await shop_service.complete_order(order_id)
    
    await callback_query.message.answer(f"Заказ {order_id} завершен.")
