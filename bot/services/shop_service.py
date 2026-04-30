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
        
        # Для предотвращения гонок при покупке, блокируем пользователя на время транзакции
        async with self.user_repository.lock_user(user_id):
            # Получаем актуальный баланс пользователя
            user = await self.user_repository.get_user_by_telegram_id(user_id)
            if not user or user.balance < product.price:
                return False
            
            # Списываем деньги с пользователя
            await self.user_repository.update_user_balance(user_id, -product.price)
            
            # Добавляем транзакцию
            await self.transaction_repository.add_transaction(
                user_id=user_id,
                amount=-product.price,
                balance_after=user.balance - product.price,
                reason=f"Покупка товара: {product.name}"
            )
            
            # Обновляем статистику
            await self.statistics_repository.update_spent_crystals(user_id, product.price)
            await self.statistics_repository.update_transactions(user_id, 1)

        return True

    
