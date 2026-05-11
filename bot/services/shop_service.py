"""Сервис для работы с магазином."""

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.product import Product
from bot.repositories.product_repository import ProductRepository
from bot.repositories.transaction_repository import TransactionRepository
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.user_repository import UserRepository
from bot.repositories.order_repository import OrderRepository
from bot.core.config import config


class ShopService:
    """Сервис для работы с магазином."""

    def __init__(self, session: AsyncSession):
        self.product_repository = ProductRepository(session)
        self.transaction_repository = TransactionRepository(session)
        self.statistics_repository = StatisticsRepository(session)
        self.user_repository = UserRepository(session)
        self.order_repository = OrderRepository(session)

    
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
        
        # Если заказ с типом manual, то создаем заказ
        if product.delivery_type == "manual":
            await self.order_repository.create_order(user_id, product_id, 1)
        
        await self.user_repository.session.commit()
        return True

    
    async def get_all_open_orders(self) -> list:
        """Получение всех открытых заказов."""
        return await self.order_repository.get_all_open_orders()
    
    
    async def complete_order(self, order_id: int) -> bool:
        """Завершение заказа."""
        order = await self.order_repository.get_order_by_id(order_id)
        if not order:
            return False
        
        await self.order_repository.complete_order(order_id)
        return True
