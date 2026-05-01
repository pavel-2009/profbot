"""Роутер для магазина."""

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.core.db import async_session_factory
from bot.dependencies import get_shop_service
from bot.core.config import config


router = Router()


def get_shop_text(products: list, page: int, total_pages: int) -> str:
    """Собрать текст страницы магазина."""
    text = "🛒 Магазин\n\n"

    for number, product in enumerate(products, start=1):
        description = f"\n{product.description}" if product.description else ""
        text += f"{number}. {product.name} - {product.price} кристаллов{description}\n\n"

    text += f"Страница {page + 1}/{total_pages}"
    return text


def get_shop_keyboard(pages: list, page: int) -> InlineKeyboardMarkup:
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
                InlineKeyboardButton(text=str(number), callback_data=f"shop_buy:{product.id}")
                for number, product in enumerate(pages[page], start=1)
            ],
        ]
    )


async def get_shop_pages() -> list:
    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        return await shop_service.get_all_products()


@router.message(Command("shop"))
@router.message(F.text == "🛒 Магазин")
async def shop(message: types.Message) -> None:
    """Обработчик команды /shop."""
    pages = await get_shop_pages()

    if not pages:
        await message.answer("Магазин пока пуст. Загляните позже!")
        return

    await message.answer(
        get_shop_text(pages[0], page=0, total_pages=len(pages)),
        reply_markup=get_shop_keyboard(pages, page=0),
    )


@router.callback_query(F.data.startswith("shop_page:"))
async def shop_page(callback: types.CallbackQuery) -> None:
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


@router.callback_query(F.data.startswith("shop_buy:"))
async def shop_buy(callback: types.CallbackQuery) -> None:
    """Покупка товара."""
    
    product_id = int(callback.data.split(":")[1])

    async with async_session_factory() as session:
        shop_service = get_shop_service(session)
        success = await shop_service.buy_product(callback.from_user.id, product_id)
        
        product = await shop_service.product_repository.get_product_by_id(product_id)

    if success:
        await callback.answer("Покупка успешна!", show_alert=True)
        
        if product and product.delivery_type == "manual":
            await callback.message.answer(f"Покупка товара '{product.name}' оформлена. Ожидайте доставки от администратора.")
             
            for admin in config.ADMINS:
                await callback.bot.send_message(
                     admin,
                     f"Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) купил товар '{product.name}' (ID: {product.id}). Пожалуйста, оформите доставку.",
                )
            return
        
        return

    await callback.answer("Не удалось купить товар: недостаточно средств или товар недоступен.", show_alert=True)
    return
