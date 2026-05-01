"""Репозиторий для работы с транзакциями."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.transaction import Transaction


class TransactionRepository:
    """Репозиторий для управления транзакциями в базе данных."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
        
    async def get_transaction_by_id(self, transaction_id: int) -> Transaction | None:
        """Получить транзакцию по ее ID."""
        result = await self.session.execute(select(Transaction).where(Transaction.id == transaction_id))
        return result.scalars().first()
    
    
    async def get_transactions_by_user_id(self, user_id: int) -> list[Transaction]:
        """Получить список транзакций для конкретного пользователя."""
        result = await self.session.execute(select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()))
        return result.scalars().all()
    

    async def get_transactions_by_user_for_days(self, user_id: int, days: int) -> list[Transaction]:
        """Получить транзакции пользователя за последние N дней."""
        date_from = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.created_at >= date_from)
            .order_by(Transaction.created_at.asc())
        )
        return result.scalars().all()
