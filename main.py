"""Точка входа в приложение бота."""

import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from bot.core.db import Base, engine
from bot.core.config import config, validate_runtime_config
from bot.core.logging import setup_logging
from bot.core.redis import get_redis_client
# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from bot.models.product import Product
from bot.models.user import User
from bot.models.statistics import Statistics
from bot.models.transaction import Transaction
from bot.models.order import Order

from bot.middlewares.statistics import StatisticsMiddleware
from bot.middlewares.limiter import RateLimiterMiddleware

setup_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    """Запуск бота."""
    validate_runtime_config()
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
    bot: Bot = Bot(token=config.BOT_TOKEN)
    redis_client = get_redis_client()
    storage = RedisStorage(redis=redis_client)
    dispatcher = Dispatcher(storage=storage)
    dispatcher.message.middleware(StatisticsMiddleware())
    dispatcher.callback_query.middleware(StatisticsMiddleware())
    dispatcher.message.middleware(RateLimiterMiddleware())
    dispatcher.callback_query.middleware(RateLimiterMiddleware())
    
    # Регистрируем роутеры
    from bot.routers.start import router as start_router  
    from bot.routers.profile import router as profile_router
    from bot.routers.shop import router as shop_router
    from bot.routers.referral import router as referral_router
    from bot.routers.menu import router as menu_router
    from bot.routers.statistics import router as statistics_router
    from bot.routers.bonus import router as bonus_router
    from bot.routers.payment import router as payment_router
    from bot.routers.admin.start import router as admin_start_router
    from bot.routers.admin.orders import router as admin_orders_router
    from bot.routers.admin.users import router as admin_users_router
    from bot.routers.admin.shop import router as admin_shop_router
      
    dispatcher.include_router(start_router)
    dispatcher.include_router(profile_router)
    dispatcher.include_router(shop_router)
    dispatcher.include_router(referral_router)
    dispatcher.include_router(menu_router)
    dispatcher.include_router(statistics_router)
    dispatcher.include_router(bonus_router)
    dispatcher.include_router(payment_router)
    dispatcher.include_router(admin_start_router)
    dispatcher.include_router(admin_orders_router)
    dispatcher.include_router(admin_users_router)
    dispatcher.include_router(admin_shop_router)
    logger.info("Routers registered")
    
    # Запускаем бота
    logger.info("Bot polling started")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
