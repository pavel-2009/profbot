"""Модель транзакций для хранения информации о покупках и продажах товаров пользователями."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey

from datetime import datetime

from bot.core.db import Base


class Transaction(Base):
    """Модель транзакции."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
