"""Репозиторий для работы с пользователями."""

import logging
import random
import string
from datetime import datetime

from redis import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.redis import get_redis
from bot.models.user import User
from bot.schemas import TransactionSchema, UserProfileSchema, UserStatsSchema
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)

REFERRAL_BONUS = 50
REGISTRATION_BONUS = 100


class UserRepository:
    """Репозиторий для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis: Redis = get_redis()
        self.statistics_repository = StatisticsRepository(session)
        self.transaction_repository = TransactionRepository(session)

    async def create_user(
        self,
        telegram_id: int,
        username: str,
        first_name: str,
        last_name: str | None,
        invited_by: int | None,
    ) -> User:
        """Создание нового пользователя."""
        referral_code = await self._generate_referral_code()
        start_balance = REGISTRATION_BONUS

        try:
            new_user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                registered_at=datetime.utcnow(),
                balance=start_balance,
                referral_code=referral_code,
                invited_by=invited_by,
            )
            self.session.add(new_user)
            await self.session.flush()
            await self.statistics_repository.create_statistics(new_user.telegram_id)

            if invited_by:
                new_user.balance += REFERRAL_BONUS
                await self.session.execute(
                    update(User)
                    .where(User.telegram_id == invited_by)
                    .values(balance=User.balance + REFERRAL_BONUS)
                )
                referrer_stats = await self.statistics_repository.get_statistics_by_user_id(invited_by)
                if referrer_stats is not None:
                    referrer_stats.invited_users += 1
                    referrer_stats.earned_crystals_via_referrals += REFERRAL_BONUS

            await self.session.commit()
            await self.session.refresh(new_user)
        except Exception as error:
            logger.error(f"Ошибка при создании пользователя: {error}", exc_info=True)
            await self.session.rollback()
            raise

        return new_user

    async def get_user_by_referral_code(self, referral_code: str) -> User | None:
        """Получение пользователя по реферальному коду."""
        result = await self.session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalars().first()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получение пользователя по Telegram ID."""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalars().first()

    async def update_user_balance(self, telegram_id: int, amount: int) -> None:
        """Обновление баланса пользователя."""
        await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(balance=User.balance + amount)
        )
        await self.session.commit()

    async def get_user_profile(self, telegram_id: int) -> UserProfileSchema | None:
        """Получение профиля пользователя."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None

        stats = await self._get_user_stats(telegram_id)
        transactions = await self._get_user_transactions(user)

        return UserProfileSchema(
            telegram_id=user.telegram_id,
            name=user.first_name,
            username=f"@{user.username}",
            registration_date=user.registered_at.strftime("%Y-%m-%d"),
            balance=user.balance,
            stats=stats,
            transactions=transactions,
            referral_link=f"https://t.me/ProfBot?start={user.referral_code}",
        )
        
    async def check_user_balance(self, telegram_id: int, amount: int) -> bool:
        """Проверка баланса пользователя."""
        user = await self.get_user_by_telegram_id(telegram_id)
        
        if not user:
            return False
        
        return user.balance >= amount

    async def _generate_referral_code(self, max_retries: int = 10) -> str:
        """Генерация уникального реферального кода."""
        for attempt in range(max_retries):
            try:
                code = "".join(random.choices(string.ascii_uppercase, k=6))
                if not self.redis.exists(f"referral_code:{code}"):
                    self.redis.setex(f"referral_code:{code}", 2592000, "1")
                    logger.info(f"Generated referral code: {code}")
                    return code
            except Exception as error:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} - Error generating referral code: {error}"
                )
                if attempt == max_retries - 1:
                    logger.error(f"Failed to generate referral code after {max_retries} attempts")
                    code = f"CODE{int(datetime.utcnow().timestamp())}"[:10]
                    logger.info(f"Using fallback referral code: {code}")
                    return code

        code = f"CODE{int(datetime.utcnow().timestamp())}"[:10]
        logger.info(f"Using final fallback referral code: {code}")
        return code

    async def _get_user_stats(self, telegram_id: int) -> UserStatsSchema:
        """Получение статистики пользователя."""
        statistics = await self.statistics_repository.get_statistics_by_user_id(telegram_id)
        
        if statistics is None:
            return UserStatsSchema(
                invited_users=0,
                earned_crystals_via_referrals=0,
                spent_crystals=0,
                transactions=0,
            )
            
        invited_users = statistics.invited_users or 0
        earned_crystals_via_referrals = statistics.earned_crystals_via_referrals or 0
        spent_crystals = statistics.spent_crystals or 0
        transactions_count = statistics.transactions or 0
        
        return UserStatsSchema(
            invited_users=invited_users,
            earned_crystals_via_referrals=earned_crystals_via_referrals,
            spent_crystals=spent_crystals,
            transactions=transactions_count,
        )

    async def _get_user_transactions(self, user: User) -> list[TransactionSchema]:
        """Получение истории транзакций пользователя."""
        transactions = await self.transaction_repository.get_transactions_by_user_id(user.telegram_id)
        
        result = []
        for transaction in transactions:
            result.append(
                TransactionSchema(
                    date=transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    amount=transaction.amount,
                    description=transaction.reason,
                )
            )

        return result
