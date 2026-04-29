"""Модель для хранения статистики пользователей бота."""

from sqlalchemy import Column, Integer, DateTime, ForeignKey

from datetime import datetime

from bot.core.db import Base


class Statistics(Base):
    """Модель статистики."""

    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invited_users = Column(Integer, default=0)
    earned_crystals_via_referrals = Column(Integer, default=0)
    spent_crystals = Column(Integer, default=0)
    transactions = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    