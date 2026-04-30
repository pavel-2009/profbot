"""Репозиторий для работы со статистикой."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timedelta

from bot.models.statistics import Statistics
from bot.models.user import User


class StatisticsRepository:
    """Репозиторий для управления статистикой в базе данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_statistics_by_user_id(self, user_id: int) -> Statistics | None:
        result = await self.session.execute(select(Statistics).where(Statistics.user_id == user_id))
        return result.scalars().first()
    
    async def get_referrals(self, user_id: int) -> tuple[int, int]:
        stats = await self.get_statistics_by_user_id(user_id)
        
        total_referrals = stats.invited_users if stats else 0
        result = await self.session.execute(
            select(User).where(User.invited_by == user_id, User.registered_at >= (datetime.utcnow() - timedelta(days=7)))
        )
        active_referrals = len(result.scalars().all())
        convresion = (active_referrals / total_referrals * 100) if total_referrals > 0 else 0
        return total_referrals, active_referrals, convresion
        

    async def create_statistics(self, user_id: int) -> Statistics:
        stats = Statistics(user_id=user_id)
        self.session.add(stats)
        await self.session.flush()
        return stats

    async def increment_fields(self, user_id: int, **increments: int) -> Statistics | None:
        stats = await self.get_statistics_by_user_id(user_id)
        if not stats:
            return None
        for field, value in increments.items():
            if isinstance(value, int):
                setattr(stats, field, (getattr(stats, field) or 0) + value)
            else:
                setattr(stats, field, value)
        await self.session.flush()
        return stats
