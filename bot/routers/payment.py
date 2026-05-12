"""Роутер для ручного пополнения баланса пользователя."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

from bot.dependencies import get_user_service
from bot.services.user_service import UserService
from bot.core.db import async_session_factory
from bot.core.config import config


router = Router()


@router.message(F.text == "💰 Пополнить")
async def handle_top_up_request(message: Message) -> None:
    """Обработчик запроса на пополнение баланса."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔮100 = 10000UZS", callback_data="top_up_100"),
             InlineKeyboardButton(text="🔮200 = 20000UZS", callback_data="top_up_200")],
            [InlineKeyboardButton(text="🔮500 = 50000UZS", callback_data="top_up_500"),
             InlineKeyboardButton(text="🔮1000 = 100000UZS", callback_data="top_up_1000")],
            [InlineKeyboardButton(text="🔮2000 = 200000UZS", callback_data="top_up_2000"),
             InlineKeyboardButton(text="🔮5000 = 500000UZS", callback_data="top_up_5000")],
            [InlineKeyboardButton(text="🔮10000 = 1000000UZS", callback_data="top_up_10000")],
        ]
    )
    await message.answer("Вы можете пополнить баланс по следующим тарифам:", reply_markup=keyboard)
    
    
@router.callback_query(F.data.startswith("top_up_"))
async def handle_top_up_selection(callback_query: CallbackQuery) -> None:
    """Обработчик выбора тарифа для пополнения."""
    amount_str = callback_query.data.split("_")[2]
    try:
        amount = int(amount_str)
    except ValueError:
        await callback_query.answer("Некорректный тариф. Попробуйте снова.", show_alert=True)
        return

    await callback_query.bot.send_invoice(
        chat_id=callback_query.from_user.id,
        title="Пополнение баланса",
        description=f"Пополнение баланса на {amount} кристаллов",
        payload=f"top_up_{amount}_{callback_query.from_user.id}",
        provider_token=config.PAYMENT_TOKEN,
        currency="UZS",
        prices=[LabeledPrice(label=f"Пополнение на {amount} кристаллов", amount=amount * 100)],
        start_parameter=f"top_up_{amount}"
    )
    
    
@router.pre_checkout_query(F.invoice_payload.startswith("top_up_"))
async def handle_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    """Обработчик предварительной проверки платежа."""
    await pre_checkout_query.answer(ok=True)
    
    
@router.message(F.content_type == "successful_payment")
async def handle_successful_payment(message: Message) -> None:
    """Обработчик успешного платежа."""
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("top_up_"):
        return  # Не наш платеж, игнорируем

    amount_str = payload.split("_")[2]
    try:
        amount = int(amount_str)
    except ValueError:
        return  # Некорректный payload, игнорируем
    
    user_id = message.from_user.id
    payment_user_id = int(payload.split("_")[3])
    
    if user_id != payment_user_id:
        return  # Платеж не от того пользователя, игнорируем

    async with async_session_factory() as session:
        user_service: UserService = get_user_service(session)
        await user_service.apply_balance_transaction(user_id, amount, description="Пополнение баланса через Telegram Payments")
        
    await message.answer(f"Ваш баланс успешно пополнен на {amount} кристаллов! Спасибо за покупку.")
    