"""Репозиторий для работы с транзакциями."""

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
    
    
    async def add_transaction(self, user_id: int, amount: int, balance_after: int, reason: str) -> Transaction:
        """Добавить новую транзакцию в базу данных."""
        new_transaction = Transaction(
            user_id=user_id,
            amount=amount,
            balance_after=balance_after,
            reason=reason,
        )
        self.session.add(new_transaction)
        await self.session.commit()
        await self.session.refresh(new_transaction)
        return new_transaction
    
    
    async def delete_transaction(self, transaction_id: int) -> bool:
        """Удалить транзакцию из базы данных."""
        transaction = await self.get_transaction_by_id(transaction_id)
        if not transaction:
            return False
        
        await self.session.delete(transaction)
        await self.session.commit()
        return True
