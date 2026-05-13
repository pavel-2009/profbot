"""Basic repository tests."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.order import OrderStatus
from bot.models.product import DeliveryType
from bot.models.transaction import Transaction
from bot.repositories.order_repository import OrderRepository
from bot.repositories.product_repository import ProductRepository
from bot.repositories.statistics_repository import StatisticsRepository
from bot.repositories.transaction_repository import TransactionRepository
from bot.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_user_repository_creates_user_with_statistics(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check user creation with default statistics."""
    repository = UserRepository(session)

    user = await repository.create_user(
        telegram_id=1,
        username="alice",
        first_name="Alice",
        last_name=None,
        invited_by=None,
    )
    stats = await repository.statistics_repository.get_statistics_by_user_id(1)
    transactions = await repository.transaction_repository.get_transactions_by_user_id(1)

    assert user.balance == 100
    assert user.referral_code is not None
    assert stats is not None
    assert stats.transactions == 1
    assert len(transactions) == 1
    assert transactions[0].amount == 100


@pytest.mark.asyncio
async def test_user_repository_handles_referral_statistics(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check referral balance and statistics."""
    repository = UserRepository(session)
    inviter = await repository.create_user(1, "alice", "Alice", None, None)

    invited = await repository.create_user(2, "bob", "Bob", None, inviter.telegram_id)
    inviter_stats = await repository.statistics_repository.get_statistics_by_user_id(1)
    invited_stats = await repository.statistics_repository.get_statistics_by_user_id(2)
    referral_stats = await repository.statistics_repository.get_referrals(1)

    assert invited.invited_by == 1
    assert invited.balance == 150
    assert inviter_stats is not None
    assert invited_stats is not None
    assert inviter_stats.invited_users == 1
    assert inviter_stats.active_invited_users == 1
    assert inviter_stats.earned_crystals_via_referrals == 50
    assert invited_stats.earned_crystals_via_referrals == 50
    assert referral_stats == (1, 1, 100)


@pytest.mark.asyncio
async def test_user_repository_rejects_negative_balance(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check balance protection."""
    repository = UserRepository(session)
    await repository.create_user(1, "alice", "Alice", None, None)

    result = await repository.apply_balance_transaction(1, -1000, "too much")
    user = await repository.get_user_by_telegram_id(1)

    assert result is None
    assert user is not None
    assert user.balance == 100


@pytest.mark.asyncio
async def test_statistics_repository_updates_fields(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check simple statistics updates."""
    user_repository = UserRepository(session)
    await user_repository.create_user(1, "alice", "Alice", None, None)

    repository = StatisticsRepository(session)
    stats = await repository.increment_fields(
        1,
        active_sessions=1,
        commands_executed=2,
        last_activity=datetime.utcnow(),
    )

    assert stats is not None
    assert stats.active_sessions == 1
    assert stats.commands_executed == 2
    assert stats.last_activity is not None


@pytest.mark.asyncio
async def test_product_repository_creates_and_updates_product(session: AsyncSession) -> None:
    """Check product create and update."""
    repository = ProductRepository(session)

    product = await repository.add_product("Course", "Base course", 10, DeliveryType.MANUAL)
    updated = await repository.update_product(product.id, price=20, delivery_type=DeliveryType.AUTO)

    assert product.name == "Course"
    assert product.is_active is True
    assert updated is not None
    assert updated.price == 20
    assert updated.delivery_type == DeliveryType.AUTO


@pytest.mark.asyncio
async def test_order_repository_closes_order(session: AsyncSession) -> None:
    """Check order status update."""
    repository = OrderRepository(session)

    order = await repository.create_order(user_id=1, product_id=1)
    assert order.status == OrderStatus.OPEN

    await repository.complete_order(order.id)
    closed_order = await repository.get_order_by_id(order.id)

    assert closed_order is not None
    assert closed_order.status == OrderStatus.CLOSED
    assert closed_order.completed_at is not None


@pytest.mark.asyncio
async def test_transaction_repository_filters_by_days(session: AsyncSession) -> None:
    """Check transaction history for period."""
    repository = TransactionRepository(session)
    old_transaction = Transaction(
        user_id=1,
        amount=10,
        balance_after=10,
        reason="old",
        created_at=datetime.utcnow() - timedelta(days=10),
    )
    new_transaction = Transaction(
        user_id=1,
        amount=20,
        balance_after=30,
        reason="new",
        created_at=datetime.utcnow(),
    )
    session.add_all([old_transaction, new_transaction])
    await session.commit()

    transactions = await repository.get_transactions_by_user_for_days(1, 7)

    assert len(transactions) == 1
    assert transactions[0].reason == "new"
