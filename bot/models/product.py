"""Модель товаров для магазина бота."""

from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum, Boolean, DateTime

from datetime import datetime
from enum import Enum

from bot.core.db import Base


class DeliveryType(Enum):
    """Типы доставки."""

    AUTO = "auto"
    MANUAL = "manual"


class Product(Base):
    """Модель товара."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False)
    delivery_type = Column(SQLEnum(DeliveryType), nullable=False, default=DeliveryType.AUTO)
    delivery_content = Column(String, nullable=True)  # Содержимое для автоматической доставки
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
