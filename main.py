"""Точка входа в приложение бота."""

from aiogram import Bot, Dispatcher

from bot.core.db import Base, engine
from bot.core.config import config
# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from bot.models.user import User


async def main() -> None:
    """Запуск бота."""
    # Инициализация базы данных
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    dispatcher = Dispatcher()
    
    # Регистрируем роутеры
    from bot.routers.start import router as start_router    
    dispatcher.include_router(start_router)
    
    # Запускаем бота
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())