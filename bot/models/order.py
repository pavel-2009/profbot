"""Модель заказа."""

from sqlalchemy import Column, Integer, String, Float, DateTime

from bot.core.db import Base


class Order(Base):
    """Модель заказа."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    ordered_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    admin_comment = Column(String(255), nullable=True)
