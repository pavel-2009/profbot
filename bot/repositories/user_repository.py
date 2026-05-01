"""Репозиторий для работы с пользователями."""

import logging
import random
import string
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.models.transaction import Transaction
from bot.schemas import TransactionSchema, UserProfileSchema, UserStatsSchema
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.transaction_repository import TransactionRepository
from bot.core.db import execute_with_retry

logger = logging.getLogger(__name__)
REFERRAL_BONUS = 50
REGISTRATION_BONUS = 100

USER_BONUSES_PER_DAY = {
    1: 5,
    2: 7,
    3: 10,
    5: 15,
    7: 20,
}


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.statistics_repository = StatisticsRepository(session)
        self.transaction_repository = TransactionRepository(session)

# === Основные методы для работы с пользователями ===
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
    
    async def get_user_referral(self, telegram_id: int) -> str:
        user = await self.get_user_by_telegram_id(telegram_id)
        return f"https://t.me/ProfBot?start={user.referral_code}" if user else ""

    async def get_user_by_referral_code(self, referral_code: str) -> User | None:
        result = await self.session.execute(select(User).where(User.referral_code == referral_code))
        return result.scalars().first()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalars().first()

# === Методы для получения профиля и статистики пользователя ===
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

    async def get_top_users_by_balance(self, limit: int = 10) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.balance.desc()).limit(limit))
        return result.scalars().all()

    async def get_user_rank_by_balance(self, telegram_id: int) -> int | None:
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        result = await self.session.execute(select(func.count()).where(User.balance > user.balance))
        higher_balance_count = result.scalar_one()
        return higher_balance_count + 1
    
    async def get_user_last_activity(self, telegram_id: int) -> datetime | None:
        stats = await self.statistics_repository.get_statistics_by_user_id(telegram_id)
        return stats.last_activity if stats else None
    
    async def get_user_last_bonus(self, telegram_id: int) -> datetime | None:
        stats = await self.statistics_repository.get_statistics_by_user_id(telegram_id)
        return stats.last_bonus if stats else None
    
# === Методы для управления балансом и транзакциями ===
    async def apply_balance_transaction(self, telegram_id: int, amount: int, reason: str) -> User | None:
        """Применить транзакцию баланса в атомарной операции."""
        logger.info(f"Applying balance transaction for user {telegram_id}: {amount} ({reason})")
        # Получаем пользователя
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalars().first()
        if not user:
            return None
        
        # Проверяем баланс
        new_balance = user.balance + amount
        if new_balance < 0:
            return None
        
        # Обновляем баланс
        user.balance = new_balance
        
        # Добавляем запись о транзакции
        transaction = Transaction(
            user_id=telegram_id,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
        )
        self.session.add(transaction)
        logger.info(f"Transaction added for user {telegram_id}: {amount} ({reason}), new balance: {new_balance}")
        
        # Обновляем статистику
        await self.statistics_repository.increment_fields(
            telegram_id,
            transactions=1,
            spent_crystals=abs(amount) if amount < 0 else 0,
            earned_crystals_via_referrals=amount if amount > 0 and "Рефераль" in reason else 0,
        )
        logger.info(f"Statistics updated for user {telegram_id}: transactions +1, spent_crystals +{abs(amount) if amount < 0 else 0}, earned_crystals_via_referrals +{amount if amount > 0 and 'Рефераль' in reason else 0}")
        
        # Записываем в БД (вызывающий код должен вызвать session.commit())
        await execute_with_retry(self.session.flush())
        return user
    
    async def apply_daily_bonus(self, telegram_id: int) -> tuple[int, str]:
        """Применить ежедневный бонус пользователю."""
        result = await self._calculate_daily_bonus(telegram_id)
        if result is None:
            return 0, "Пользователь не найден"
        
        bonus, days_active = result
        if bonus == 0:
            return 0, "Ежедневный бонус уже получен сегодня"
        
        # Применяем бонус только один раз
        await self.apply_balance_transaction(
            telegram_id, 
            bonus, 
            f"Ежедневный бонус за {days_active} дней активности"
        )
        
        # Обновляем дату последнего получения бонуса
        stats = await self.statistics_repository.get_statistics_by_user_id(telegram_id)
        if stats:
            await self.statistics_repository.increment_fields(
                telegram_id,
                last_bonus=datetime.utcnow(),
                last_activity_track_start=stats.last_activity_track_start if days_active <= max(USER_BONUSES_PER_DAY.keys()) else datetime.utcnow()
            )
        
        return bonus, f"Ежедневный бонус в размере {bonus} кристаллов за {days_active} дней активности"

    async def _calculate_daily_bonus(self, telegram_id: int) -> tuple[int, int] | None:
        """Только вычислить бонус, БЕЗ применения. Возвращает (bonus, days_active) или None."""
        stats = await self.statistics_repository.get_statistics_by_user_id(telegram_id)
        if not stats:
            return None
        
        now = datetime.utcnow()
        if stats.last_bonus and (now - stats.last_activity).days < 1:
            return 0, 0
        
        days_active = (now - stats.last_activity_track_start).days + 1
        bonus = USER_BONUSES_PER_DAY.get(days_active, max(USER_BONUSES_PER_DAY.values()))
        logger.info(f"Calculating daily bonus for user {telegram_id}: {days_active} days active, bonus: {bonus}")
        return bonus, days_active

    async def _generate_referral_code(self, max_retries: int = 10) -> str:
        for _ in range(max_retries):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if await self.get_user_by_referral_code(code) is None:
                return code
        return f"CODE{int(datetime.utcnow().timestamp())}"[:10]

    async def _get_user_stats(self, telegram_id: int) -> UserStatsSchema:
        statistics = await self.statistics_repository.get_statistics_by_user_id(telegram_id)
        referral_stats = await self.statistics_repository.get_referrals(telegram_id)
        if statistics is None:
            return UserStatsSchema()
        return UserStatsSchema(
            invited_users=referral_stats[0],
            active_invited_users=referral_stats[1],
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
