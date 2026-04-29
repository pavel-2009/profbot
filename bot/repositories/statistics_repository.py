"""Репозиторий для работы со статистикой."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.transaction import Transaction
from bot.models.user import User
from bot.models.statistics import Statistics


class StatisticsRepository:
    """Репозиторий для управления статистикой в базе данных."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
        
    async def get_statistics_by_user_id(self, user_id: int) -> Statistics | None:
        """Получить статистику для конкретного пользователя."""
        result = await self.session.execute(
            select(Statistics).where(Statistics.user_id == user_id)
        )
        return result.scalars().first()
    
    
    async def update_invited_users(self, user_id: int, invited_users: int) -> Statistics | None:
        """Обновить количество приглашенных друзей в статистике."""
        stats = await self.get_statistics_by_user_id(user_id)
        if not stats:
            return None
        
        stats.invited_users = invited_users
        await self.session.commit()
        await self.session.refresh(stats)
        return stats
    
    
    async def update_earned_crystals_via_referrals(self, user_id: int, earned_crystals: int) -> Statistics | None:
        """Обновить количество заработанных кристаллов по рефералке в статистике."""
        stats = await self.get_statistics_by_user_id(user_id)
        if not stats:
            return None
        
        stats.earned_crystals_via_referrals = earned_crystals
        await self.session.commit()
        await self.session.refresh(stats)
        return stats
    
    
    async def update_spent_crystals(self, user_id: int, spent_crystals: int) -> Statistics | None:
        """Обновить количество потраченных кристаллов в статистике."""
        stats = await self.get_statistics_by_user_id(user_id)
        if not stats:
            return None
        
        stats.spent_crystals = spent_crystals
        await self.session.commit()
        await self.session.refresh(stats)
        return stats
    
    
    async def update_transactions(self, user_id: int, transactions: int) -> Statistics | None:
        """Обновить количество транзакций в статистике."""
        stats = await self.get_statistics_by_user_id(user_id)
        if not stats:
            return None
        
        stats.transactions = transactions
        await self.session.commit()
        await self.session.refresh(stats)
        return stats
