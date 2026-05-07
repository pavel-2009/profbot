"""Мидлварь для проверки прав администратора."""

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from typing import Any, Awaitable, Callable

from bot.core.config import config


class AdminMiddleware(BaseMiddleware):
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        
        admins = config.ADMINS
        
        if user and user.id in admins:
            return await handler(event, data)
        
        else:
            if isinstance(event, Message):
                await event.reply("У вас нет прав для выполнения этой команды.")
                
            return None
