"""Роутер для ручного пополнения баланса пользователя."""

import asyncio
import logging

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.core.config import config
from bot.core.db import async_session_factory
from bot.dependencies import get_user_service
from bot.services.user_service import UserService
from bot.core.redis import get_redis_client


router = Router()
logger = logging.getLogger(__name__)
redis_client = get_redis_client()
ALLOWED_TOP_UP_AMOUNTS = {100, 200, 500, 1000, 2000, 5000, 10000}
MAX_TOP_UP_RETRIES = 3
TOP_UP_RETRY_DELAY_SECONDS = 1


def _parse_top_up_payload(payload: str) -> tuple[int, int] | None:
    """Распарсить payload формата top_up_{amount}_{user_id}."""
    parts = payload.split("_")
    if len(parts) != 4 or parts[0] != "top" or parts[1] != "up":
        return None

    try:
        amount = int(parts[2])
        payment_user_id = int(parts[3])
    except ValueError:
        return None

    if amount not in ALLOWED_TOP_UP_AMOUNTS or payment_user_id <= 0:
        return None

    return amount, payment_user_id


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

    if amount not in ALLOWED_TOP_UP_AMOUNTS:
        await callback_query.answer("Такой тариф недоступен.", show_alert=True)
        return

    try:
        await callback_query.bot.send_invoice(
            chat_id=callback_query.from_user.id,
            title="Пополнение баланса",
            description=f"Пополнение баланса на {amount} кристаллов",
            payload=f"top_up_{amount}_{callback_query.from_user.id}",
            provider_token=config.PAYMENT_TOKEN,
            currency="UZS",
            prices=[LabeledPrice(label=f"Пополнение на {amount} кристаллов", amount=amount * 100)],
            start_parameter=f"top_up_{amount}",
        )
        
        # Сохранение информации о платеже в Redis для последующей проверки
        await redis_client.setex(f"pending_top_up:{callback_query.from_user.id}:{amount}", 3600, "pending")
        
        await callback_query.answer("Счёт на оплату отправлен.")
    except Exception:
        logger.exception("Failed to send top up invoice", extra={"user_id": callback_query.from_user.id, "amount": amount})
        await callback_query.answer("Не удалось создать счёт. Попробуйте позже.", show_alert=True)


@router.pre_checkout_query(F.invoice_payload.startswith("top_up_"))
async def handle_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    """Обработчик предварительной проверки платежа."""
    payload_data = _parse_top_up_payload(pre_checkout_query.invoice_payload)
    if payload_data is None:
        await pre_checkout_query.answer(ok=False, error_message="Некорректные данные платежа.")
        return

    amount, payment_user_id = payload_data
    if pre_checkout_query.from_user.id != payment_user_id:
        await pre_checkout_query.answer(ok=False, error_message="Платёж можно оплатить только владельцу счёта.")
        return

    total_amount = pre_checkout_query.total_amount
    expected_total_amount = amount * 100
    if total_amount != expected_total_amount:
        await pre_checkout_query.answer(ok=False, error_message="Сумма платежа не совпадает с тарифом.")
        return
    
    if await redis_client.get(f"pending_top_up:{payment_user_id}:{amount}") != b"pending":
        return

    await pre_checkout_query.answer(ok=True)


@router.message(F.content_type == "successful_payment")
async def handle_successful_payment(message: Message) -> None:
    """Обработчик успешного платежа."""
    payment = message.successful_payment
    payload_data = _parse_top_up_payload(payment.invoice_payload)
    if payload_data is None:
        logger.warning("Received successful payment with invalid payload", extra={"payload": payment.invoice_payload})
        return

    amount, payment_user_id = payload_data

    user_id = message.from_user.id
    if user_id != payment_user_id:
        logger.warning("Payment user mismatch", extra={"message_user_id": user_id, "payload_user_id": payment_user_id})
        return

    expected_total_amount = amount * 100
    if payment.total_amount != expected_total_amount:
        logger.warning(
            "Payment amount mismatch",
            extra={"user_id": user_id, "expected_total_amount": expected_total_amount, "actual_total_amount": payment.total_amount},
        )
        await message.answer("Платёж получен с некорректной суммой. Обратитесь в поддержку.")
        return

    for attempt in range(1, MAX_TOP_UP_RETRIES + 1):
        try:
            async with async_session_factory() as session:
                user_service: UserService = get_user_service(session)
                if not await user_service.user_exists(user_id):
                    await message.answer("Пользователь не найден. Напишите /start и повторите пополнение.")
                    return

                updated_user = await user_service.apply_balance_transaction(
                    user_id,
                    amount,
                    reason="Пополнение баланса через Telegram Payments",
                    payment_charge_id=payment.telegram_payment_charge_id,
                )

                if updated_user is None:
                    raise RuntimeError("Balance top up transaction returned None")

            await message.answer(f"Ваш баланс успешно пополнен на {amount} кристаллов! Спасибо за покупку.")
            
            await redis_client.delete(f"pending_top_up:{user_id}:{amount}")
            
            return
        except Exception:
            logger.exception("Top up attempt failed", extra={"user_id": user_id, "amount": amount, "attempt": attempt})
            if attempt == MAX_TOP_UP_RETRIES:
                await message.answer(
                    "Платёж получен, но зачисление временно недоступно. Мы уже зафиксировали ошибку и проверим вручную."
                )
                return
            await asyncio.sleep(TOP_UP_RETRY_DELAY_SECONDS)
            
        finally:
            await redis_client.delete(f"pending_top_up:{user_id}:{amount}")
            return
