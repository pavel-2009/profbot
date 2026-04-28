"""Роутер для стартового сообщения."""

import logging

from aiogram import Router, types
from aiogram.filters import CommandObject, CommandStart

from bot.core.db import async_session_factory
from bot.dependencies import get_user_service
from bot.keyboards.keyboards import main_menu_keyboard
from bot.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def start(message: types.Message, command: CommandObject) -> None:
    """Обработчик команды /start."""
    referral_code = (command.args or "").strip() or None

    try:
        async with async_session_factory() as session:
            user_service: UserService = get_user_service(session)

            if await user_service.user_exists(message.from_user.id):
                logger.info(f"User {message.from_user.id} already registered")
                await message.answer("Вы уже зарегистрированы.", reply_markup=main_menu_keyboard)
                return

            referrer = None
            if referral_code:
                referrer = await user_service.get_user_by_referral_code(referral_code)
                if referrer is None:
                    logger.warning(
                        f"Invalid referral code '{referral_code}' used by user {message.from_user.id}"
                    )
                    await message.answer(
                        "Ошибка: реферальный код недействителен. Проверьте код и попробуйте снова."
                    )
                    return

                if referrer.telegram_id == message.from_user.id:
                    logger.warning(
                        f"User {message.from_user.id} attempted to use their own referral code"
                    )
                    await message.answer("Ошибка: нельзя использовать собственный реферальный код.")
                    return

            telegram_id = message.from_user.id
            username = message.from_user.username or f"user_{telegram_id}"
            first_name = message.from_user.first_name or "Пользователь"
            last_name = message.from_user.last_name

            await user_service.register_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                invited_by=referrer.telegram_id if referrer else None,
            )

            referral_bonus_text = "\n🎁 +50 кристаллов за регистрацию по реферальному коду!" if referrer else ""
            await message.answer(
                (
                    f"👋 Добро пожаловать, {first_name}!\n\n"
                    "Вы успешно зарегистрированы в ProfBot.\n"
                    f"Ваш ID: {telegram_id}\n\n"
                    "🎁 +100 кристаллов за регистрацию!"
                    f"{referral_bonus_text}\n\n"
                    "Используйте /help, чтобы посмотреть список команд."
                ),
                reply_markup=main_menu_keyboard,
            )
            logger.info(f"User {telegram_id} successfully registered")
    except Exception as error:
        logger.error(f"Error occurred while handling /start command: {error}", exc_info=True)
        await message.answer("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
