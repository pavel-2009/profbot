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
        user = await self.user_repository.get_user_by_telegram_id(user_id)
        if user is None:
            return False

        await self.transaction_repository.add_transaction(
            user_id=user_id,
            amount=-product.price,
            balance_after=user.balance,
            reason=f"Покупка товара: {product.name}",
        )

        stats = await self.statistics_repository.get_statistics_by_user_id(user_id)
        if stats is not None:
            stats.spent_crystals += product.price
            stats.transactions += 1
            await self.statistics_repository.session.commit()

        return True

    
