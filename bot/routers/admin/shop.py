"""Роутер для управления магазином."""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.models.product import Product, DeliveryType
from bot.core.db import async_session_factory
from bot.dependencies import get_shop_service
from bot.routers.shop import get_shop_text, get_shop_pages
from bot.middlewares.admin import AdminMiddleware
from bot.core.redis import redis_lock

logger = logging.getLogger(__name__)


# === FSM States ===
class EditProductForm(StatesGroup):
    """Состояния для редактирования товара."""
    waiting_for_product_id = State()
    waiting_for_field = State()
    waiting_for_new_value = State()
    
    
class AddProductForm(StatesGroup):
    """Состояния для добавления товара."""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_delivery_type = State()
    waiting_for_confirmation = State()


def get_shop_keyboard(pages: list[Product], page: int) -> InlineKeyboardMarkup:
    """Клавиатура магазина."""
    total_pages = len(pages)
    prev_page = max(page - 1, 0)
    next_page = min(page + 1, total_pages - 1)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️", callback_data=f"shop_page:{prev_page}"),
                InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=f"shop_page:{page}"),
                InlineKeyboardButton(text="➡️", callback_data=f"shop_page:{next_page}"),
            ],
            [
                InlineKeyboardButton(text=str(number), callback_data=f"shop_edit:{product.id}")
                for number, product in enumerate(pages[page], start=1)
            ],
        ]
    )


def get_edit_field_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Название", callback_data="edit_name")],
            [InlineKeyboardButton(text="📄 Описание", callback_data="edit_description")],
            [InlineKeyboardButton(text="💰 Цена", callback_data="edit_price")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")],
        ]
    )


router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


@router.message(F.text == "🛒 Управление товарами")
async def get_products_list(message: Message, state: FSMContext) -> None:
    """Получения списка товаров."""
    await state.clear()
    
    product_list = await get_shop_pages()
    
    if not product_list:
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить товар")],
                [KeyboardButton(text="⬅️ Назад в меню")]
            ]
        )
        
        await message.answer("Нет товаров в магазине.", reply_markup=keyboard)
        return
    
    products = get_shop_text(product_list[0], page=0, total_pages=len(product_list))
    keyboard = get_shop_keyboard(product_list, page=0)
    
    await message.answer(products, reply_markup=keyboard)
    
    
@router.callback_query(F.data.startswith("shop_page:"))
async def shop_page(callback: CallbackQuery) -> None:
    """Переключение страниц магазина."""
    pages = await get_shop_pages()

    if not pages:
        await callback.answer("Магазин пока пуст.")
        return

    page = int(callback.data.split(":")[1])
    page = max(0, min(page, len(pages) - 1))

    await callback.message.edit_text(
        get_shop_text(pages[page], page=page, total_pages=len(pages)),
        reply_markup=get_shop_keyboard(pages, page=page),
    )
    await callback.answer()
    

# === Редактирование товара ===
@router.callback_query(F.data.startswith("shop_edit:"))
async def shop_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования товара."""
    product_id = int(callback.data.split(":")[1])
    async with redis_lock(f"admin:shop_edit:{callback.from_user.id}:{product_id}") as acquired:
        if not acquired:
            await callback.answer("⏳ Запрос уже обрабатывается")
            return

        async with async_session_factory() as session:
            shop_service = get_shop_service(session)
            product = await shop_service.get_product_by_id(product_id)
    
    if not product:
        await callback.message.answer("Товар не найден.")
        await callback.answer()
        return
    
    product_info = (
        f"📝 Товар для редактирования:\n\n"
        f"<b>ID:</b> {product.id}\n"
        f"<b>Название:</b> {product.name}\n"
        f"<b>Описание:</b> {product.description or 'Не указано'}\n"
        f"<b>Цена:</b> {product.price} 🔮\n"
    )
    
    await state.set_state(EditProductForm.waiting_for_field)
    await state.update_data(product_id=product_id)
    await callback.message.answer(product_info, parse_mode="HTML")
    await callback.message.answer("Что вы хотите изменить?", reply_markup=get_edit_field_keyboard())
    await callback.answer()


@router.callback_query(EditProductForm.waiting_for_field, F.data.startswith("edit_"))
async def process_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора поля для редактирования."""
    field_map = {
        "edit_name": ("name", "Введите новое название товара:"),
        "edit_description": ("description", "Введите новое описание товара:"),
        "edit_price": ("price", "Введите новую цену товара (в кристаллах):"),
    }
    
    field_name, prompt = field_map.get(callback.data, (None, None))
    if not field_name:
        await callback.answer()
        return
    
    await state.update_data(edit_field=field_name)
    await state.set_state(EditProductForm.waiting_for_new_value)
    await callback.message.answer(prompt)
    await callback.answer()


@router.callback_query(EditProductForm.waiting_for_field, F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена редактирования."""
    await state.clear()
    await callback.message.answer("❌ Редактирование отменено.")
    await callback.answer()


@router.message(EditProductForm.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext) -> None:
    """Обработка нового значения поля."""
    data = await state.get_data()
    field = data['edit_field']
    product_id = data['product_id']
    
    # Validation
    if field == "price":
        try:
            price = int(message.text)
            if price <= 0:
                await message.answer("Цена должна быть положительным числом.")
                return
        except ValueError:
            await message.answer("Введите корректное число.")
            return
        new_value = price
    else:
        new_value = message.text
    
    try:
        async with redis_lock(f"admin:product_update:{message.from_user.id}:{product_id}") as acquired:
            if not acquired:
                await message.answer("⏳ Изменение уже обрабатывается")
                return
            async with async_session_factory() as session:
                shop_service = get_shop_service(session)
                update_data = {field: new_value}
                product = await shop_service.update_product(product_id, **update_data)
            
            if product:
                logger.info(f"Product {product_id} field '{field}' updated")
                await message.answer(
                    f"✅ Товар успешно обновлён!\n\n"
                    f"<b>Поле:</b> {field}\n"
                    f"<b>Новое значение:</b> {new_value}",
                    parse_mode="HTML"
                )
            else:
                await message.answer("❌ Товар не найден.")
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        await message.answer("❌ Ошибка при обновлении товара.")
    
    await state.clear()


# === Добавление товара ===
@router.message(F.text == "➕ Добавить товар")
async def add_product_start(message: Message, state: FSMContext) -> None:
    """Начало добавления товара."""
    await state.set_state(AddProductForm.waiting_for_name)
    await message.answer("Введите название нового товара:")
    
    
@router.message(AddProductForm.waiting_for_name)
async def add_product_name(message: Message, state: FSMContext) -> None:
    """Обработка названия нового товара."""
    
    if not message.text.strip():
        await message.answer("Название не может быть пустым. Пожалуйста, введите корректное название:")
        return
    
    if len(message.text) > 100:
        await message.answer("Название слишком длинное. Максимальная длина - 100 символов. Пожалуйста, введите более короткое название:")
        return
    
    await state.update_data(name=message.text)
    await state.set_state(AddProductForm.waiting_for_description)
    await message.answer("Введите описание нового товара:")
    
    
@router.message(AddProductForm.waiting_for_description)
async def add_product_description(message: Message, state: FSMContext) -> None:
    """Обработка описания нового товара."""
    if not message.text.strip():
        await message.answer("Описание не может быть пустым. Пожалуйста, введите корректное описание:")
        return
    
    if len(message.text) > 500:
        await message.answer("Описание слишком длинное. Максимальная длина - 500 символов. Пожалуйста, введите более короткое описание:")
        return

    await state.update_data(description=message.text)
    await state.set_state(AddProductForm.waiting_for_price)
    await message.answer("Введите цену нового товара (в кристаллах):")
    
    
@router.message(AddProductForm.waiting_for_price)
async def add_product_price(message: Message, state: FSMContext) -> None:
    """Обработка цены нового товара."""
    try:
        price = int(message.text)
        
        if price <= 0:
            await message.answer("Цена должна быть положительным числом. Пожалуйста, введите корректную цену:")
            return
        
    except ValueError:
        await message.answer("Введите корректное число для цены:")
        return
    
    await state.update_data(price=price)
    await state.set_state(AddProductForm.waiting_for_delivery_type)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Manual (ручная выдача)", callback_data="delivery_manual")],
            [InlineKeyboardButton(text="Automatic (автоматическая выдача)", callback_data="delivery_auto")],
        ]
    )
    
    await message.answer("Введите тип доставки нового товара (manual/auto):", reply_markup=keyboard)
    
    
@router.callback_query(AddProductForm.waiting_for_delivery_type, F.data.startswith("delivery_"))
async def add_product_delivery_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка типа доставки нового товара."""
    delivery_type = callback.data.split("_")[1]
    
    if delivery_type not in ["manual", "auto"]:
        await callback.message.answer("Некорректный тип доставки. Пожалуйста, выберите один из предложенных вариантов.")
        return
    
    await state.update_data(delivery_type=delivery_type)
    await state.set_state(AddProductForm.waiting_for_confirmation)
    
    data = await state.get_data()
    confirmation_text = (
        f"Пожалуйста, подтвердите добавление нового товара:\n\n"
        f"<b>Название:</b> {data['name']}\n"
        f"<b>Описание:</b> {data['description']}\n"
        f"<b>Цена:</b> {data['price']} 🔮\n"
        f"<b>Тип доставки:</b> {data['delivery_type']}\n\n"
        f"Вы уверены, что хотите добавить этот товар?"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_add_product")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_add_product")],
        ]
    )
    
    await callback.message.answer(confirmation_text, parse_mode="HTML", reply_markup=keyboard)
    
    
@router.callback_query(AddProductForm.waiting_for_confirmation, F.data == "confirm_add_product")
async def add_product_delivery_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Загрузка нового товара в базу данных."""
    
    data = await state.get_data()
    
    try:
        async with async_session_factory() as session:
            shop_service = get_shop_service(session)
            new_product = await shop_service.add_product(
                name=data['name'],
                description=data['description'],
                price=data['price'],
                delivery_type=DeliveryType.AUTO if data['delivery_type'] == "auto" else DeliveryType.MANUAL)
            
            
            if new_product:
                logger.info(f"New product added: {new_product.id} - {new_product.name}")
                await callback.message.answer(
                    f"✅ Товар успешно добавлен!\n\n"
                    f"<b>ID:</b> {new_product.id}\n"
                    f"<b>Название:</b> {new_product.name}\n"
                    f"<b>Описание:</b> {new_product.description}\n"
                    f"<b>Цена:</b> {new_product.price} 🔮\n"
                    f"<b>Тип доставки:</b> {new_product.delivery_type}",
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer("❌ Не удалось добавить товар.")
    except Exception as e:
        logger.error(f"Error adding product: {e}")
        await callback.message.answer("❌ Ошибка при добавлении товара.")
        await state.clear()
        return
    
    await state.clear()
    
    
@router.callback_query(AddProductForm.waiting_for_confirmation, F.data == "cancel_add_product")
async def cancel_add_product(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена добавления нового товара."""
    await state.clear()
    await callback.message.answer("❌ Добавление товара отменено.")
