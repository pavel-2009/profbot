"""Модель пользователя для бота."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, BigInteger

from bot.core.db import Base


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    registered_at = Column(DateTime, nullable=False)
    balance = Column(Integer, default=0)
    referral_code = Column(String, unique=True, nullable=True)
    invited_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)

    # создаем индексы
    __table_args__ = (
        Index("idx_users_telegram_id", "telegram_id"),
        Index("idx_users_username", "username"),
        Index("idx_users_referral_code", "referral_code")
    )
