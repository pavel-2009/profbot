"""Модель заказа."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, Integer, String, ForeignKey, BigInteger

from bot.core.db import Base


class OrderStatus(Enum):
    """Статусы заказа."""

    OPEN = "open"
    CLOSED = "closed"


class Order(Base):
    """Модель заказа."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    status = Column(SqlEnum(OrderStatus), nullable=False, default=OrderStatus.OPEN)
    ordered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    admin_comment = Column(String(255), nullable=True)
