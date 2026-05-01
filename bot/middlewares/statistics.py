"""Мидлварь для корректного подсчёта пользовательской активности."""

import asyncio
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from typing import Any, Awaitable, Callable
from datetime import datetime
import logging

from bot.repositories.statistics_repository import StatisticsRepository

logger = logging.getLogger(__name__)


class StatisticsMiddleware(BaseMiddleware):
    """Сохраняет статистику заходов и выполненных команд в БД (фоновый процесс)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Запускаем обновление статистики в фоне (не блокируем обработку события)
        user = getattr(event, "from_user", None)
        if user:
            asyncio.create_task(self._update_statistics(user.id, event))
        
        # Основной handler выполняется без задержки
        return await handler(event, data)

    async def _update_statistics(self, user_id: int, event: TelegramObject) -> None:
        """Обновить статистику пользователя (фоновый процесс)."""
        try:
            from bot.core.db import async_session_factory
            
            async with async_session_factory() as session:
                repository = StatisticsRepository(session)
                stats = await repository.get_statistics_by_user_id(user_id)
                if stats:
                    increments = {"last_activity": datetime.utcnow()}
                    if self._is_visit_event(event):
                        increments["active_sessions"] = 1
                    if self._is_command_event(event):
                        increments["commands_executed"] = 1
                    await repository.increment_fields(user_id, **increments)
                    await session.commit()
                    logger.info(f"Updated statistics for user {user_id}: {increments}")
                    
        except Exception as e:
            logger.error(f"Error updating statistics for user {user_id}: {e}", exc_info=True)
            pass

    @staticmethod
    def _is_visit_event(event: TelegramObject) -> bool:
        if not isinstance(event, Message) or not event.text:
            return False
        return event.text.startswith("/start") or event.text == "📚 Главная"

    @staticmethod
    def _is_command_event(event: TelegramObject) -> bool:
        return isinstance(event, Message) and bool(event.text and event.text.startswith("/"))
