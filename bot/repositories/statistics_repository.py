"""Репозиторий для работы со статистикой."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.order import Order, OrderStatus
from bot.models.product import DeliveryType, Product
from bot.models.statistics import Statistics
from bot.models.transaction import Transaction
from bot.models.user import User


class StatisticsRepository:
    """Репозиторий для управления статистикой в базе данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_statistics(self, user_id: int) -> Statistics:
        stats = Statistics(user_id=user_id)
        self.session.add(stats)
        await self.session.flush()
        return stats

    async def get_statistics_by_user_id(self, user_id: int) -> Statistics | None:
        result = await self.session.execute(select(Statistics).where(Statistics.user_id == user_id))
        return result.scalars().first()

    async def get_referrals(self, user_id: int) -> tuple[int, int, int]:
        stats = await self.get_statistics_by_user_id(user_id)

        total_referrals = stats.invited_users if stats else 0
        result = await self.session.execute(
            select(User).where(User.invited_by == user_id, User.registered_at >= (datetime.utcnow() - timedelta(days=7)))
        )
        active_referrals = len(result.scalars().all())
        conversion = int((active_referrals / total_referrals) * 100) if total_referrals > 0 else 0
        return total_referrals, active_referrals, conversion

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

    async def get_admin_global_stats(self) -> dict[str, int]:
        """Собирает агрегированную статистику для админов."""
        total_users = (await self.session.execute(select(func.count()).select_from(User))).scalar_one()
        total_balance = (await self.session.execute(select(func.coalesce(func.sum(User.balance), 0)))).scalar_one()
        total_products = (await self.session.execute(select(func.count()).select_from(Product))).scalar_one()
        auto_products = (
            await self.session.execute(select(func.count()).where(Product.delivery_type == DeliveryType.AUTO))
        ).scalar_one()
        manual_products = (
            await self.session.execute(select(func.count()).where(Product.delivery_type == DeliveryType.MANUAL))
        ).scalar_one()
        total_orders = (await self.session.execute(select(func.count()).select_from(Order))).scalar_one()
        open_orders = (await self.session.execute(select(func.count()).where(Order.status == OrderStatus.OPEN))).scalar_one()
        total_transactions = (await self.session.execute(select(func.count()).select_from(Transaction))).scalar_one()
        economy_turnover = (
            await self.session.execute(select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0)))
        ).scalar_one()

        return {
            "total_users": total_users,
            "total_balance": total_balance,
            "total_products": total_products,
            "auto_products": auto_products,
            "manual_products": manual_products,
            "total_orders": total_orders,
            "open_orders": open_orders,
            "total_transactions": total_transactions,
            "economy_turnover": economy_turnover,
        }
