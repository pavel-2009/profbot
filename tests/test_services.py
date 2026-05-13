"""Basic service tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.order import OrderStatus
from bot.models.product import DeliveryType
from bot.repositories.order_repository import OrderRepository
from bot.services.shop_service import ShopService
from bot.services.user_service import UserService


@pytest.mark.asyncio
async def test_user_service_registers_user(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check user registration service."""
    service = UserService(session)

    user = await service.register_user(1, "alice", "Alice", None, None)
    exists = await service.user_exists(1)
    profile = await service.get_user_profile(1)
    referral = await service.get_user_referral(1)

    assert user.telegram_id == 1
    assert exists is True
    assert profile is not None
    assert profile.balance == 100
    assert profile.stats.transactions == 1
    assert referral.endswith(user.referral_code)


@pytest.mark.asyncio
async def test_user_service_updates_balance_and_statistics(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check balance operation service."""
    service = UserService(session)
    await service.register_user(1, "alice", "Alice", None, None)

    user = await service.apply_balance_transaction(1, -30, "shop")
    profile = await service.get_user_profile(1)

    assert user is not None
    assert user.balance == 70
    assert profile is not None
    assert profile.stats.spent_crystals == 30
    assert profile.stats.transactions == 2


@pytest.mark.asyncio
async def test_user_service_returns_referral_statistics(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check referral statistics service."""
    service = UserService(session)
    inviter = await service.register_user(1, "alice", "Alice", None, None)
    await service.register_user(2, "bob", "Bob", None, inviter.telegram_id)

    stats = await service.get_referrals_stats(1)

    assert stats == (1, 1, 100)


@pytest.mark.asyncio
async def test_shop_service_buys_auto_product(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check auto product purchase."""
    user_service = UserService(session)
    shop_service = ShopService(session)
    await user_service.register_user(1, "alice", "Alice", None, None)
    product = await shop_service.add_product("Auto", "Auto delivery", 40, DeliveryType.AUTO)

    result = await shop_service.buy_product(1, product.id)
    profile = await user_service.get_user_profile(1)
    orders = await shop_service.get_all_open_orders()

    assert result is True
    assert profile is not None
    assert profile.balance == 60
    assert profile.stats.spent_crystals == 40
    assert orders == []


@pytest.mark.asyncio
async def test_shop_service_buys_manual_product_and_creates_order(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check manual product purchase."""
    user_service = UserService(session)
    shop_service = ShopService(session)
    await user_service.register_user(1, "alice", "Alice", None, None)
    product = await shop_service.add_product("Manual", "Manual delivery", 50, DeliveryType.MANUAL)

    result = await shop_service.buy_product(1, product.id)
    orders = await shop_service.get_all_open_orders()

    assert result is True
    assert len(orders) == 1
    assert orders[0].user_id == 1
    assert orders[0].product_id == product.id
    assert orders[0].status == OrderStatus.OPEN


@pytest.mark.asyncio
async def test_shop_service_rejects_purchase_without_balance(
    session: AsyncSession,
    redis_client: object,
) -> None:
    """Check purchase without enough balance."""
    user_service = UserService(session)
    shop_service = ShopService(session)
    await user_service.register_user(1, "alice", "Alice", None, None)
    product = await shop_service.add_product("Expensive", "Manual delivery", 200, DeliveryType.MANUAL)

    result = await shop_service.buy_product(1, product.id)
    orders = await OrderRepository(session).get_all_open_orders()
    profile = await user_service.get_user_profile(1)

    assert result is False
    assert orders == []
    assert profile is not None
    assert profile.balance == 100
