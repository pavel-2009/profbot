"""Репозиторий для работы со статистикой."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.statistics import Statistics


class StatisticsRepository:
    """Репозиторий для управления статистикой в базе данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_statistics_by_user_id(self, user_id: int) -> Statistics | None:
        result = await self.session.execute(select(Statistics).where(Statistics.user_id == user_id))
        return result.scalars().first()

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
            setattr(stats, field, (getattr(stats, field) or 0) + value)
        await self.session.flush()
        return stats
