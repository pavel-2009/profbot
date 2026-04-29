"""Сервис для работы с магазином."""

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.product import Product
from bot.repositories.product_repository import ProductRepository
from bot.repositories.transaction_repository import TransactionRepository
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.user_repository import UserRepository
from bot.core.config import config


class ShopService:
    """Сервис для работы с магазином."""

    def __init__(self, session: AsyncSession):
        self.product_repository = ProductRepository(session)
        self.transaction_repository = TransactionRepository(session)
        self.statistics_repository = StatisticsRepository(session)
        self.user_repository = UserRepository(session)

    
    async def get_all_products(self) -> list[list[Product]]:
        """Получение всех товаров."""
        return await self.product_repository.get_all_products()
    
    
    async def buy_product(self, user_id: int, product_id: int) -> bool:
        """Покупка товара пользователем."""
        product = await self.product_repository.get_product_by_id(product_id)
        if not product:
            return False
        
        if not await self.user_repository.check_user_balance(user_id, product.price):
            return False

        await self.user_repository.update_user_balance(user_id, -product.price)
        await self.transaction_repository.add_transaction(user_id=user_id, amount=product.price, description=f"Покупка товара: {product.name}")
        await self.statistics_repository.update_spent_crystals(user_id, product.price)
        
        return True

    
