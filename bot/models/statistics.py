"""Модель для хранения статистики пользователей бота."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from bot.core.db import Base


class Statistics(Base):
    """Модель статистики."""

    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    invited_users = Column(Integer, default=0)
    active_invited_users = Column(Integer, default=0)
    active_sessions = Column(Integer, default=0)
    commands_executed = Column(Integer, default=0)
    earned_crystals_via_referrals = Column(Integer, default=0)
    spent_crystals = Column(Integer, default=0)
    transactions = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
