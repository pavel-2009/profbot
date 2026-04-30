"""Pydantic-схемы для контрактов профиля пользователя."""

from pydantic import BaseModel, Field


class TransactionSchema(BaseModel):
    """Схема одной транзакции пользователя."""

    date: str
    amount: int
    description: str


class UserStatsSchema(BaseModel):
    """Схема статистики пользователя."""

    invited_users: int = Field(default=0)
    active_invited_users: int = Field(default=0)
    active_sessions: int = Field(default=0)
    commands_executed: int = Field(default=0)
    earned_crystals_via_referrals: int = Field(default=0)
    spent_crystals: int = Field(default=0)
    transactions: int = Field(default=0)


class UserProfileSchema(BaseModel):
    """Схема профиля пользователя."""

    telegram_id: int
    name: str
    username: str
    registration_date: str
    balance: int
    stats: UserStatsSchema
    transactions: list[TransactionSchema]
    referral_link: str
