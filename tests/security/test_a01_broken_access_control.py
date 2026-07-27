"""Detection tests for OWASP A01 — Broken Access Control (iter-10)."""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.application.use_cases.revenue import GetStoreRevenue
from ecommerce_backoffice_api.domain.entities import Order, OrderLine, Store, User
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError

pytestmark = pytest.mark.security


class _FakeStoreRepository:
    def __init__(self, stores: list[Store]) -> None:
        self._stores = stores

    def list_all(self) -> list[Store]:
        return list(self._stores)

    def get_by_id(self, store_id: int) -> Store | None:
        for store in self._stores:
            if store.id == store_id:
                return store
        return None

    def get_by_public_id(self, public_id: str) -> Store | None:
        for store in self._stores:
            if store.public_id == public_id:
                return store
        return None

    def add(self, store: Store) -> Store:
        return store


class _FakeOrderRepository:
    def __init__(self, orders: list[Order]) -> None:
        self._orders = orders

    def list_for_store(self, store_id: int) -> list[Order]:
        return [order for order in self._orders if order.store_id == store_id]

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        return [
            order
            for order in self._orders
            if order.store_id == store_id and order.customer_user_id == customer_user_id
        ]

    def get_by_id(self, order_id: int) -> Order | None:
        for order in self._orders:
            if order.id == order_id:
                return order
        return None

    def add(self, order: Order) -> Order:
        return order

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        raise NotImplementedError

    def update_notes(self, order_id: int, notes: str) -> Order:
        raise NotImplementedError


def _stores() -> list[Store]:
    return [
        Store(id=1, public_id="8a1f3d7a-cf7e-4a27-a2e8-47142f5be7ac", name="Store A", owner_user_id=11),
        Store(id=2, public_id="f8c7f0d9-2360-4f91-921a-1550c8e5b4b2", name="Store B", owner_user_id=12),
    ]


def _orders() -> list[Order]:
    return [
        Order(
            id=10,
            store_id=1,
            customer_user_id=201,
            status=OrderStatus.CONFIRMED,
            customer_email="c1@example.test",
            customer_full_name="C One",
            shipping_address="A",
            lines=[OrderLine(product_id=1, quantity=2, unit_price_cents=1500)],
        ),
        Order(
            id=11,
            store_id=1,
            customer_user_id=202,
            status=OrderStatus.CANCELLED,
            customer_email="c2@example.test",
            customer_full_name="C Two",
            shipping_address="B",
            lines=[OrderLine(product_id=1, quantity=1, unit_price_cents=999)],
        ),
    ]


def test_cross_store_revenue_must_be_blocked_for_other_store_owner() -> None:
    # Threat category: OWASP A01 (Broken Access Control).
    # Attack path: a store owner from tenant B requests revenue for tenant A.
    # Expected secure behavior: authorization must fail before any sensitive data is returned.
    # Failure impact: cross-tenant financial disclosure and privilege abuse.
    # Arrange
    owner_from_store_b = User(
        id=12,
        email="ownerb@example.test",
        password_hash="unused",
        role=UserRole.STORE_OWNER,
        full_name="Owner B",
        store_id=2,
    )
    use_case = GetStoreRevenue(_FakeStoreRepository(_stores()), _FakeOrderRepository(_orders()))

    # Act + Assert
    with pytest.raises(AuthorizationError):
        use_case.execute(
            actor=owner_from_store_b,
            store_public_id="8a1f3d7a-cf7e-4a27-a2e8-47142f5be7ac",
        )


def test_store_revenue_must_use_uuid_lookup_and_authorized_scope() -> None:
    # Threat category: OWASP A01 (Broken Access Control).
    # Attack path: an authorized owner queries store revenue through public identifiers.
    # Expected secure behavior: lookup stays within actor scope and only tenant-owned data is aggregated.
    # Failure impact: identifier confusion may expose or mix another tenant's data.
    # Arrange
    owner_from_store_a = User(
        id=11,
        email="ownera@example.test",
        password_hash="unused",
        role=UserRole.STORE_OWNER,
        full_name="Owner A",
        store_id=1,
    )
    use_case = GetStoreRevenue(_FakeStoreRepository(_stores()), _FakeOrderRepository(_orders()))

    # Act
    result = use_case.execute(
        actor=owner_from_store_a,
        store_public_id="8a1f3d7a-cf7e-4a27-a2e8-47142f5be7ac",
    )

    # Assert
    assert result.store_name == "Store A"
    assert result.total_orders == 2
    assert result.paid_orders == 1
    assert result.gross_revenue_cents == 3000
