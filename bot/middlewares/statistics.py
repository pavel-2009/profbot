"""Миддлварь для базового подсчёта активности пользователя."""

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from typing import Any, Awaitable, Callable
from datetime import datetime

from bot.core.db import async_session_factory
from bot.repositories.statistics_repository import StatisticsRepository


class StatisticsMiddleware(BaseMiddleware):
    """Сохраняет базовую активность пользователя в БД."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user:
            async with async_session_factory() as session:
                repository = StatisticsRepository(session)
                stats = await repository.get_statistics_by_user_id(user.id)
                if stats:
                    increments = {"active_sessions": 1}
                    if self._is_command_event(event):
                        increments["commands_executed"] = 1
                    increments["last_activity"] = datetime.utcnow()  # Обновляем время последней активности
                    await repository.increment_fields(user.id, **increments)
                    await session.commit()
        return await handler(event, data)

    @staticmethod
    def _is_command_event(event: TelegramObject) -> bool:
        if isinstance(event, Message):
            return bool(event.text and event.text.startswith("/"))
        if isinstance(event, CallbackQuery):
            return True
        return False
