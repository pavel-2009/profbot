"""Точка входа в приложение бота."""

import logging
import asyncio
from aiogram import Bot, Dispatcher

from bot.core.db import Base, engine
from bot.core.config import config
# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from bot.models.product import Product
from bot.models.user import User
from bot.models.statistics import Statistics
from bot.models.transaction import Transaction

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
    from bot.routers.shop import router as shop_router
    from bot.routers.referral import router as referral_router
    from bot.routers.menu import router as menu_router
      
    dispatcher.include_router(start_router)
    dispatcher.include_router(profile_router)
    dispatcher.include_router(shop_router)
    dispatcher.include_router(referral_router)
    dispatcher.include_router(menu_router)
    logger.info("Routers registered")
    
    # Запускаем бота
    logger.info("Bot polling started")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
