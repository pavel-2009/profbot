"""Точка входа в приложение бота."""

import logging
import asyncio
from aiogram import Bot, Dispatcher

from bot.core.db import Base, engine
from bot.core.config import config
# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from bot.models.user import User

# Конфигурируем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Запуск бота."""
    logger.info("Starting bot...")
    
    # Инициализация базы данных
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    dispatcher = Dispatcher()
    
    # Регистрируем роутеры
    from bot.routers.start import router as start_router  
    from bot.routers.profile import router as profile_router
      
    dispatcher.include_router(start_router)
    dispatcher.include_router(profile_router)
    logger.info("Routers registered")
    
    # Запускаем бота
    logger.info("Bot polling started")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())