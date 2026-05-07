"""Модель заказа."""

from sqlalchemy import Column, Integer, String, DateTime, Enum as SqlEnum

from enum import Enum

from bot.core.db import Base


class OrderStatus(Enum):
    open = "open"
    closed = "closed"


class Order(Base):
    """Модель заказа."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    status = Column(SqlEnum(OrderStatus), nullable=False, default=OrderStatus.open)
    ordered_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    admin_comment = Column(String(255), nullable=True)
