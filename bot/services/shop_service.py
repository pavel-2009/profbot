"""Сервис для работы с магазином."""

import asyncio
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import config
from bot.models.order import Order
from bot.models.product import DeliveryType, Product
from bot.repositories.order_repository import OrderRepository
from bot.repositories.product_repository import ProductRepository
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.transaction_repository import TransactionRepository
from bot.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class ShopService:
    """Сервис для работы с магазином."""

    def __init__(self, session: AsyncSession):
        self.product_repository = ProductRepository(session)
        self.transaction_repository = TransactionRepository(session)
        self.statistics_repository = StatisticsRepository(session)
        self.user_repository = UserRepository(session)
        self.order_repository = OrderRepository(session)

    async def add_product(self, name: str, description: str, price: int, delivery_type: str) -> Product:
        """Добавление нового товара."""
        return await self.product_repository.add_product(name, description, price, delivery_type)

    async def get_all_products(self) -> list[list[Product]]:
        """Получение всех товаров."""
        return await self.product_repository.get_all_products()

    async def buy_product(self, user_id: int, product_id: int) -> bool:
        """Покупка товара пользователем."""
        product = await self.product_repository.get_product_by_id(product_id)
        if not product:
            return False

        user = await self.user_repository.apply_balance_transaction(
            user_id,
            -product.price,
            f"Покупка товара: {product.name}",
        )
        if user is None:
            return False

        if product.delivery_type == DeliveryType.MANUAL:
            await self.order_repository.create_order(user_id, product_id)

        await self.user_repository.session.commit()
        return True

    async def get_all_open_orders(self) -> list[Order]:
        """Получение всех открытых заказов."""
        return await self.order_repository.get_all_open_orders()

    async def get_order_by_id(self, order_id: int) -> Order | None:
        """Получение заказа по ID."""
        return await self.order_repository.get_order_by_id(order_id)

    async def complete_order(self, order_id: int) -> bool:
        """Завершение заказа."""
        order = await self.order_repository.get_order_by_id(order_id)
        if not order:
            return False

        await self.order_repository.complete_order(order_id)
        return True

    async def get_admin_global_stats(self) -> dict[str, int]:
        """Получение агрегированной статистики для админского контура."""
        return await self.statistics_repository.get_admin_global_stats()

    async def notify_admins_about_new_order(self, bot: Bot, user_id: int, product: Product) -> bool:
        """Надежно отправляет уведомление о новом manual-заказе всем админам."""
        if not config.ADMINS:
            logger.warning("ADMINS is empty, order notification skipped")
            return False

        text = (
            "🔔 Новый manual-заказ\n"
            f"Пользователь: {user_id}\n"
            f"Товар: {product.name} (ID: {product.id})\n"
            "Проверьте /orders"
        )

        async def _send_to_admin(admin_id: int) -> bool:
            for attempt in range(1, 4):
                try:
                    await bot.send_message(admin_id, text)
                    return True
                except Exception:
                    logger.exception("Failed to notify admin=%s about order=%s (attempt %s)", admin_id, product.id, attempt)
                    await asyncio.sleep(0.5 * attempt)
            return False

        results = await asyncio.gather(*[_send_to_admin(admin_id) for admin_id in config.ADMINS])
        return all(results)

    async def get_product_by_id(self, product_id: int) -> Product | None:
        """Получение товара по ID."""
        return await self.product_repository.get_product_by_id(product_id)

    async def update_product(self, product_id: int, **kwargs) -> Product | None:
        """Обновление товара."""
        return await self.product_repository.update_product(product_id, **kwargs)
