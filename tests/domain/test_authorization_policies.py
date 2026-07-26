"""Unit smoke tests for domain authorization policies (no database)."""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import Order, User
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole

pytestmark = pytest.mark.smoke


def _user(role: UserRole, *, user_id: int = 1, store_id: int | None = 1) -> User:
    return User(
        id=user_id,
        email=f"{role.value}@example.test",
        password_hash="unused",
        role=role,
        full_name=role.value,
        store_id=store_id,
    )


def _order(*, store_id: int = 1, customer_user_id: int = 10) -> Order:
    return Order(
        id=100,
        store_id=store_id,
        customer_user_id=customer_user_id,
        status=OrderStatus.PACKED,
        customer_email="customer@example.test",
        customer_full_name="Casey Customer",
        shipping_address="1 Demo Way",
    )


def test_admin_can_read_any_store_and_order() -> None:
    admin = _user(UserRole.ADMIN, store_id=None)
    order = _order(store_id=2, customer_user_id=99)

    assert authorization.can_read_store(admin, 2)
    assert authorization.can_read_order(admin, order)
    assert authorization.can_update_order_status(admin, order)
    assert not authorization.must_anonymize_order_for(admin)


def test_store_owner_is_tenant_scoped() -> None:
    owner = _user(UserRole.STORE_OWNER, store_id=1)
    own_order = _order(store_id=1)
    other_order = _order(store_id=2)

    assert authorization.can_write_store_catalog(owner, 1)
    assert not authorization.can_write_store_catalog(owner, 2)
    assert authorization.can_read_order(owner, own_order)
    assert not authorization.can_read_order(owner, other_order)


def test_customer_reads_own_orders_only() -> None:
    customer = _user(UserRole.CUSTOMER, user_id=10, store_id=1)
    own_order = _order(store_id=1, customer_user_id=10)
    other_order = _order(store_id=1, customer_user_id=11)

    assert authorization.can_read_store_catalog(customer, 1)
    assert not authorization.can_write_store_catalog(customer, 1)
    assert authorization.can_read_order(customer, own_order)
    assert not authorization.can_read_order(customer, other_order)
    assert not authorization.can_update_order_status(customer, own_order)


def test_delivery_manager_sees_anonymized_orders() -> None:
    delivery = _user(UserRole.DELIVERY_MANAGER, store_id=None)
    order = _order()

    assert authorization.can_read_order(delivery, order)
    assert authorization.can_update_order_status(delivery, order)
    assert authorization.must_anonymize_order_for(delivery)
    assert not authorization.can_write_store_catalog(delivery, 1)


def test_only_admin_may_list_users_and_audit_events() -> None:
    admin = _user(UserRole.ADMIN, store_id=None)
    owner = _user(UserRole.STORE_OWNER, store_id=1)
    customer = _user(UserRole.CUSTOMER, store_id=1)
    delivery = _user(UserRole.DELIVERY_MANAGER, store_id=None)

    assert authorization.can_list_users(admin)
    assert authorization.can_list_audit_events(admin)
    assert not authorization.can_list_users(owner)
    assert not authorization.can_list_audit_events(owner)
    assert not authorization.can_list_users(customer)
    assert not authorization.can_list_audit_events(delivery)
