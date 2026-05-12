"""Репозиторий для работы с заказами в базе данных."""

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.order import Order, OrderStatus


class OrderRepository:
    """Репозиторий для работы с заказами в базе данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, user_id: int, product_id: int) -> Order:
        """Создает новый заказ."""
        new_order = Order(user_id=user_id, product_id=product_id)
        self.session.add(new_order)
        await self.session.flush()
        await self.session.refresh(new_order)
        return new_order

    async def get_orders_by_user(self, user_id: int) -> list[Order]:
        """Получает все заказы пользователя."""
        result = await self.session.execute(select(Order).where(Order.user_id == user_id))
        
        return result.scalars().all()
    
    async def get_order_by_id(self, order_id: int) -> Order | None:
        """Получает заказ по его ID."""
        result = await self.session.execute(select(Order).where(Order.id == order_id))
        
        return result.scalars().first()
    
    async def get_all_open_orders(self) -> list[Order]:
        """Получает все открытые заказы."""
        result = await self.session.execute(select(Order).where(Order.status == OrderStatus.OPEN))
        return result.scalars().all()

    async def complete_order(self, order_id: int) -> None:
        """Завершает заказ."""
        await self.update_order_status(order_id, OrderStatus.CLOSED)

    async def update_order_status(self, order_id: int, new_status: OrderStatus) -> None:
        """Обновляет статус заказа."""
        values = {"status": new_status}
        if new_status == OrderStatus.CLOSED:
            values["completed_at"] = datetime.utcnow()
        await self.session.execute(update(Order).where(Order.id == order_id).values(**values))
        await self.session.commit()

    async def delete_order(self, order_id: int) -> None:
        """Удаляет заказ."""
        await self.session.execute(delete(Order).where(Order.id == order_id))
        await self.session.commit()
