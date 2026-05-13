"""Блокировка пользователя при превышении лимита запросов."""

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.core.config import config
from bot.core.redis import get_redis_client


class RateLimiterMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        redis_client = get_redis_client()
        
        # Получаем текущее количество запросов для пользователя
        current_count = await redis_client.get(f"rate_limit:{user_id}")
        
        if current_count is None:
            # Если ключ не существует, создаем его с начальным значением 1 и устанавливаем время жизни
            await redis_client.set(f"rate_limit:{user_id}", 1, ex=config.RATE_LIMIT_TIME)
        else:
            current_count = int(current_count)
            if current_count >= config.RATE_LIMIT_MAX_REQUESTS:
                # Если превышен лимит, отправляем сообщение и блокируем выполнение обработчика
                await event.answer("Вы превысили лимит запросов. Пожалуйста, попробуйте позже.")
                return
            else:
                # Увеличиваем счетчик запросов
                await redis_client.incr(f"rate_limit:{user_id}")
        
        # Продолжить выполнение обработчика
        return await handler(event, data)
