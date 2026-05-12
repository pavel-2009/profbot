"""Минимальные unit-тесты репозиториев."""

import unittest

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.core.db import Base
from bot.models.order import OrderStatus
from bot.models.product import DeliveryType
from bot.repositories.order_repository import OrderRepository
from bot.repositories.product_repository import ProductRepository
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.user_repository import UserRepository

# Импорты нужны, чтобы модели зарегистрировались в Base.metadata.
from bot.models import order, product, statistics, transaction, user  # noqa: F401


class RepositoryTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_user_repository_creates_user_statistics_and_registration_bonus(self) -> None:
        async with self.session_factory() as session:
            repo = UserRepository(session)

            created = await repo.create_user(
                telegram_id=1,
                username="alice",
                first_name="Alice",
                last_name=None,
                invited_by=None,
            )
            stats = await repo.statistics_repository.get_statistics_by_user_id(created.telegram_id)
            transactions = await repo.transaction_repository.get_transactions_by_user_id(created.telegram_id)

            self.assertEqual(created.balance, 100)
            self.assertIsNotNone(created.referral_code)
            self.assertIsNotNone(stats)
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0].reason, "Бонус за регистрацию")

    async def test_balance_transaction_rejects_negative_balance(self) -> None:
        async with self.session_factory() as session:
            repo = UserRepository(session)
            await repo.create_user(telegram_id=1, username="alice", first_name="Alice", last_name=None, invited_by=None)

            result = await repo.apply_balance_transaction(telegram_id=1, amount=-1000, reason="Too much")
            user = await repo.get_user_by_telegram_id(1)

            self.assertIsNone(result)
            self.assertEqual(user.balance, 100)

    async def test_statistics_repository_updates_bonus_state(self) -> None:
        async with self.session_factory() as session:
            stats_repo = StatisticsRepository(session)
            await stats_repo.create_statistics(user_id=1)

            stats = await stats_repo.increment_fields(user_id=1, invited_users=1, active_invited_users=1)

            self.assertIsNotNone(stats)
            self.assertEqual(stats.invited_users, 1)
            self.assertEqual(stats.active_invited_users, 1)

    async def test_product_repository_creates_manual_product(self) -> None:
        async with self.session_factory() as session:
            repo = ProductRepository(session)

            product = await repo.add_product(
                name="Manual",
                description="Manual delivery",
                price=10,
                delivery_type=DeliveryType.MANUAL,
            )

            self.assertEqual(product.delivery_type, DeliveryType.MANUAL)
            self.assertTrue(product.is_active)

    async def test_order_repository_uses_defaults_and_closes_order(self) -> None:
        async with self.session_factory() as session:
            repo = OrderRepository(session)

            order = await repo.create_order(user_id=1, product_id=2)
            self.assertEqual(order.status, OrderStatus.OPEN)
            self.assertIsNotNone(order.ordered_at)

            await repo.complete_order(order.id)
            closed = await repo.get_order_by_id(order.id)

            self.assertEqual(closed.status, OrderStatus.CLOSED)
            self.assertIsNotNone(closed.completed_at)


if __name__ == "__main__":
    unittest.main()
