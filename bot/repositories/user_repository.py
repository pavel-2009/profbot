"""Репозиторий для работы с пользователями."""

import logging
import random
import string
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.schemas import TransactionSchema, UserProfileSchema, UserStatsSchema
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)
REFERRAL_BONUS = 50
REGISTRATION_BONUS = 100


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.statistics_repository = StatisticsRepository(session)
        self.transaction_repository = TransactionRepository(session)

    async def create_user(self, telegram_id: int, username: str, first_name: str, last_name: str | None, invited_by: int | None) -> User:
        referral_code = await self._generate_referral_code()
        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            registered_at=datetime.utcnow(),
            balance=0,
            referral_code=referral_code,
            invited_by=invited_by,
        )
        self.session.add(new_user)
        await self.session.flush()
        await self.statistics_repository.create_statistics(new_user.telegram_id)
        await self.apply_balance_transaction(telegram_id, REGISTRATION_BONUS, "Бонус за регистрацию")
        if invited_by:
            await self.apply_balance_transaction(telegram_id, REFERRAL_BONUS, "Реферальный бонус новому пользователю")
            await self.apply_balance_transaction(invited_by, REFERRAL_BONUS, f"Реферальный бонус за приглашение пользователя {telegram_id}")
            await self.statistics_repository.increment_fields(invited_by, invited_users=1, active_invited_users=1)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def get_user_by_referral_code(self, referral_code: str) -> User | None:
        result = await self.session.execute(select(User).where(User.referral_code == referral_code))
        return result.scalars().first()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalars().first()

    async def apply_balance_transaction(self, telegram_id: int, amount: int, reason: str) -> User | None:
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None
        new_balance = user.balance + amount
        if new_balance < 0:
            return None
        user.balance = new_balance
        await self.transaction_repository.add_transaction(telegram_id, amount, new_balance, reason)
        await self.statistics_repository.increment_fields(
            telegram_id,
            transactions=1,
            spent_crystals=abs(amount) if amount < 0 else 0,
            earned_crystals_via_referrals=amount if amount > 0 and "Рефераль" in reason else 0,
        )
        await self.session.flush()
        return user

    async def get_user_referral(self, telegram_id: int) -> str:
        user = await self.get_user_by_telegram_id(telegram_id)
        return f"https://t.me/ProfBot?start={user.referral_code}" if user else ""

    async def get_invited_users(self, telegram_id: int) -> list[UserProfileSchema]:
        result = await self.session.execute(select(User).where(User.invited_by == telegram_id))
        invited_users = result.scalars().all()
        profiles = []
        for user in invited_users:
            stats = await self.statistics_repository.get_statistics_by_user_id(user.telegram_id)
            profiles.append(UserProfileSchema(
                telegram_id=user.telegram_id,
                name=user.first_name,
                username=f"@{user.username}",
                registration_date=user.registered_at.strftime("%Y-%m-%d"),
                balance=user.balance,
                stats=UserStatsSchema(
                    invited_users=stats.invited_users if stats else 0,
                    active_invited_users=stats.active_invited_users if stats else 0,
                    active_sessions=stats.active_sessions if stats else 0,
                    commands_executed=stats.commands_executed if stats else 0,
                    earned_crystals_via_referrals=stats.earned_crystals_via_referrals if stats else 0,
                    spent_crystals=stats.spent_crystals if stats else 0,
                    transactions=stats.transactions if stats else 0,
                ),
                transactions=[],
                referral_link=f"https://t.me/ProfBot?start={user.referral_code}",
            ))
        return profiles

    async def get_user_profile(self, telegram_id: int) -> UserProfileSchema | None:
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None
        return UserProfileSchema(
            telegram_id=user.telegram_id,
            name=user.first_name,
            username=f"@{user.username}",
            registration_date=user.registered_at.strftime("%Y-%m-%d"),
            balance=user.balance,
            stats=await self._get_user_stats(telegram_id),
            transactions=await self._get_user_transactions(user),
            referral_link=f"https://t.me/ProfBot?start={user.referral_code}",
        )

    async def _generate_referral_code(self, max_retries: int = 10) -> str:
        for _ in range(max_retries):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if await self.get_user_by_referral_code(code) is None:
                return code
        return f"CODE{int(datetime.utcnow().timestamp())}"[:10]

    async def _get_user_stats(self, telegram_id: int) -> UserStatsSchema:
        statistics = await self.statistics_repository.get_statistics_by_user_id(telegram_id)
        if statistics is None:
            return UserStatsSchema()
        return UserStatsSchema(
            invited_users=statistics.invited_users or 0,
            active_invited_users=statistics.active_invited_users or 0,
            active_sessions=statistics.active_sessions or 0,
            commands_executed=statistics.commands_executed or 0,
            earned_crystals_via_referrals=statistics.earned_crystals_via_referrals or 0,
            spent_crystals=statistics.spent_crystals or 0,
            transactions=statistics.transactions or 0,
        )

    async def _get_user_transactions(self, user: User) -> list[TransactionSchema]:
        transactions = await self.transaction_repository.get_transactions_by_user_id(user.telegram_id)
        return [
            TransactionSchema(date=t.created_at.strftime("%Y-%m-%d %H:%M:%S"), amount=t.amount, description=t.reason)
            for t in transactions
        ]
