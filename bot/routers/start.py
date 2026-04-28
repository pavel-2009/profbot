"""Роутер для стартового сообщения."""

import logging
from aiogram import Router, types
from aiogram.filters import CommandStart, CommandObject

from bot.services.user_service import UserService
from bot.dependencies import get_user_service
from bot.core.db import get_async_session
from bot.keyboards.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())    
async def start(message: types.Message, command: CommandObject) -> None:
    """Обработчик команды /start."""
    
    try:
        async for session in get_async_session():
            try:
                user_service: UserService = await get_user_service(session)
                
                if await user_service.user_exists(message.from_user.id):
                    logger.info(f"User {message.from_user.id} already registered")
                    await message.answer("Вы уже зарегистрированы!", reply_markup=main_menu_keyboard)
                    return
                
                # Проверяем наличие реферального кода в аргументах команды
                referral_code = command.args if command.args else None
                
                if referral_code:
                    
                    referrer = await user_service.get_user_by_referral_code(referral_code)
                    
                    if referrer is None:
                        logger.warning(f"Invalid referral code '{referral_code}' used by user {message.from_user.id}")
                        await message.answer("Неверный реферальный код.")
                        return
                        
                    elif referrer.telegram_id == message.from_user.id:
                        logger.warning(f"User {message.from_user.id} attempted to use their own referral code")
                        await message.answer("Вы не можете использовать свой собственный реферальный код. Регистрация без реферала.", reply_markup=main_menu_keyboard)
                        return
                    
                    else:
                        logger.info(f"User {message.from_user.id} referred by user {referrer.telegram_id} with code '{referral_code}'")
                
                telegram_id = message.from_user.id
                username = message.from_user.username or f"user_{telegram_id}"
                first_name = message.from_user.first_name or "Пользователь"
                last_name = message.from_user.last_name or "Пользователь"
                
                await user_service.register_user(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    invited_by=referrer.telegram_id if referrer else None
                )
                await message.answer(
                    f"""👋 Добро пожаловать, {first_name}!\n\n
Ты автоматически зарегистрирован в системе "ProfBot".\n
Твой ID в системе: {telegram_id}\n\n

🎁 Тебе начислено 100 кристаллов за регистрацию!\n\n

Используй /help, чтобы увидеть список команд.""",
                    reply_markup=main_menu_keyboard
                )
                logger.info(f"User {telegram_id} successfully registered")
                return
            
            except Exception as e:
                logger.error(f"Error in session handler: {e}", exc_info=True)
                await message.answer("Произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже.")
                raise

    except Exception as e:
        logger.error(f"Error occurred while handling /start command: {e}", exc_info=True)
        try:
            await message.answer("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
            return 
        except Exception as msg_error:
            logger.error(f"Failed to send error message: {msg_error}")
            return