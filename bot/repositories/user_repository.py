"""Репозиторий для работы с пользователями."""

from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis

from datetime import datetime
import random
import string

from bot.models.user import User
from bot.core.db import get_async_session
from bot.core.redis import get_redis


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
        referral_code = self._generate_referral_code()
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
        
        
    def _generate_referral_code(self) -> str:
        """Генерация уникального реферального кода."""
        
        while True:
            try:
                
                chars = string.ascii_uppercase
                code = ''.join(random.choices(chars, k=6))
                if not self.redis.exists(f"referral_code:{code}"):
                    return code
            except Exception as e:
                
                print(f"Ошибка при генерации реферального кода: {e}")
                continue