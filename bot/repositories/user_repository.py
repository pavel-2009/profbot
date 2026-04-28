"""Репозиторий для работы с пользователями."""

import logging
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis

from datetime import datetime
import random
import string

from bot.models.user import User
from bot.core.db import get_async_session
from bot.core.redis import get_redis

logger = logging.getLogger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis: Redis = get_redis()
        
        
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

        try: 
            new_user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                registered_at=datetime.utcnow(),
                balance=100,  # начальный баланс
                referral_code=referral_code,
                invited_by=invited_by,
            )
        
            self.session.add(new_user)
            await self.session.commit()
            await self.session.refresh(new_user)
            
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}", exc_info=True)
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
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalars().first()
    
    
    async def update_user_balance(self, telegram_id: int, amount: int) -> None:
        """Обновление баланса пользователя."""
        await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(balance=User.balance + amount)
        )
        await self.session.commit()
        
        
    async def get_user_profile(self, telegram_id: int) -> User | None:
        """Получение профиля пользователя."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        
        user: User = result.scalars().first()
        if user:
            # Извлекаем данные
            telegram_id = user.telegram_id
            name = user.first_name
            username =  "@" + user.username
            registration_date = user.registered_at.strftime("%Y-%m-%d")
            balance = user.balance
            stats = await self._get_user_stats(telegram_id)
            transactions = await self._get_user_transactions(telegram_id)
            referal_link = f"https://t.me/ProfBot?start={user.referral_code}"
        
        return {
            "telegram_id": telegram_id,
            "name": name,
            "username": username,
            "registration_date": registration_date,
            "balance": balance,
            "stats": stats,
            "transactions": transactions,
            "referral_link": referal_link
        }


    async def _generate_referral_code(self, max_retries: int = 10) -> str:
        """Генерация уникального реферального кода."""
        
        for attempt in range(max_retries):
            try:
                chars = string.ascii_uppercase
                code = ''.join(random.choices(chars, k=6))
                
                if not self.redis.exists(f"referral_code:{code}"):
                    # Сохраняем код в Redis с TTL 30 дней
                    self.redis.setex(f"referral_code:{code}", 2592000, "1")
                    logger.info(f"Generated referral code: {code}")
                    return code
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - Error generating referral code: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to generate referral code after {max_retries} attempts")
                    # Возвращаем code на основе timestamp как fallback
                    code = f"CODE{int(datetime.utcnow().timestamp())}"[:10]
                    logger.info(f"Using fallback referral code: {code}")
                    return code
                continue
            
            
    async def _get_user_stats(self, telegram_id: int) -> dict:
        """Получение статистики пользователя."""
        # Здесь можно реализовать логику получения статистики из базы данных
        # Например, количество приглашенных пользователей, заработанные кристаллы и т.д.
        return {
            "invited_users": 5,  # пример данных
            "earned_crystals_via_referrals": 200,  # пример данных
            "spent_crystals": 150,  # пример данных
            "transactions": 10,  # пример данных
        }
        
        
    async def _get_user_transactions(self, telegram_id: int) -> list:
        """Получение истории транзакций пользователя."""
        # Здесь можно реализовать логику получения транзакций из базы данных
        return [
            {"date": "2024-01-01", "amount": 100, "description": "Реферальный бонус"},  # пример данных
            {"date": "2024-01-02", "amount": -50, "description": "Покупка: ""Доступ к VIP чату"""},  # пример данных
        ]