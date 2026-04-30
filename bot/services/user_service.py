"""Сервис для работы с пользователями."""

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.repositories.user_repository import UserRepository
from bot.schemas import UserProfileSchema


class UserService:
    """Сервис для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.user_repository = UserRepository(session)

    async def register_user(
        self,
        telegram_id: int,
        username: str,
        first_name: str,
        last_name: str | None,
        invited_by: int | None,
    ) -> User:
        """Регистрация нового пользователя."""
        return await self.user_repository.create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            invited_by=invited_by,
        )

    async def user_exists(self, telegram_id: int) -> bool:
        """Проверка существования пользователя."""
        user = await self.user_repository.get_user_by_telegram_id(telegram_id)
        return user is not None

    async def get_user_by_referral_code(self, referral_code: str) -> User | None:
        """Получение пользователя по реферальному коду."""
        return await self.user_repository.get_user_by_referral_code(referral_code)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получение пользователя по Telegram ID."""
        return await self.user_repository.get_user_by_telegram_id(telegram_id)

    async def apply_balance_transaction(self, telegram_id: int, amount: int, reason: str) -> User | None:
        """Единая операция изменения баланса."""
        result = await self.user_repository.apply_balance_transaction(telegram_id, amount, reason)
        await self.user_repository.session.commit()
        return result

    async def get_user_profile(self, telegram_id: int) -> UserProfileSchema | None:
        """Получение профиля пользователя."""
        return await self.user_repository.get_user_profile(telegram_id)
    
    async def get_user_referral(self, telegram_id: int) -> str:
        """Получение реферальной ссылки пользователя."""
        return await self.user_repository.get_user_referral(telegram_id)
    
    async def get_invited_users(self, telegram_id: int) -> list[UserProfileSchema]:
        """Получение списка пользователей, приглашенных данным пользователем."""
        return await self.user_repository.get_invited_users(telegram_id)
