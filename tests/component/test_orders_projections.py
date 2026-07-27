"""Component tests for order listing, projection, and status transitions."""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.application.dto.orders import AnonymizedOrderView, OrderDetailView
from ecommerce_backoffice_api.application.use_cases.audit import AdminAuditTrail
from ecommerce_backoffice_api.application.use_cases.orders import (
    GetOrder,
    ListOrdersForStore,
    UpdateOrderNotes,
    UpdateOrderStatus,
)
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, ConflictError
from tests.component.factories import make_order, make_store, make_user
from tests.component.fakes import FakeAuditEventRepository, FakeOrderRepository, FakeStoreRepository

pytestmark = pytest.mark.component


def test_list_orders_anonymizes_for_delivery_manager_and_filters_customer() -> None:
    own = make_order(order_id=1, customer_user_id=201)
    other = make_order(order_id=2, customer_user_id=202)
    orders = FakeOrderRepository([own, other])
    stores = FakeStoreRepository([make_store()])
    use_case = ListOrdersForStore(orders, stores)

    delivery = make_user(user_id=50, role=UserRole.DELIVERY_MANAGER, store_id=None)
    delivery_views = use_case.execute(actor=delivery, store_id=1)
    assert len(delivery_views) == 2
    assert all(isinstance(view, AnonymizedOrderView) for view in delivery_views)

    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)
    customer_views = use_case.execute(actor=customer, store_id=1)
    assert len(customer_views) == 1
    assert isinstance(customer_views[0], OrderDetailView)
    assert customer_views[0].customer_user_id == 201


def test_get_order_denies_cross_tenant_owner_and_anonymizes_delivery() -> None:
    order = make_order(order_id=10, store_id=1, customer_user_id=201)
    orders = FakeOrderRepository([order])
    audit = AdminAuditTrail(FakeAuditEventRepository())
    use_case = GetOrder(orders, audit)

    foreign_owner = make_user(user_id=12, role=UserRole.STORE_OWNER, store_id=2)
    with pytest.raises(AuthorizationError):
        use_case.execute(actor=foreign_owner, order_id=10)

    delivery = make_user(user_id=50, role=UserRole.DELIVERY_MANAGER, store_id=None)
    view = use_case.execute(actor=delivery, order_id=10)
    assert isinstance(view, AnonymizedOrderView)
    assert not hasattr(view, "customer_email")


def test_update_order_status_rejects_illegal_transition_and_customer_actor() -> None:
    order = make_order(order_id=20, status=OrderStatus.DELIVERED)
    orders = FakeOrderRepository([order])
    use_case = UpdateOrderStatus(orders)

    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)
    with pytest.raises(AuthorizationError):
        use_case.execute(actor=customer, order_id=20, status=OrderStatus.CONFIRMED)

    owner = make_user(user_id=11, role=UserRole.STORE_OWNER, store_id=1)
    with pytest.raises(ConflictError, match="not permitted"):
        use_case.execute(actor=owner, order_id=20, status=OrderStatus.PENDING)


def test_update_order_status_allows_legal_owner_transition() -> None:
    order = make_order(order_id=21, status=OrderStatus.PENDING)
    orders = FakeOrderRepository([order])
    use_case = UpdateOrderStatus(orders)
    owner = make_user(user_id=11, role=UserRole.STORE_OWNER, store_id=1)

    view = use_case.execute(actor=owner, order_id=21, status=OrderStatus.CONFIRMED)
    assert view.status is OrderStatus.CONFIRMED


def test_update_order_notes_denied_for_delivery_manager() -> None:
    order = make_order(order_id=30)
    orders = FakeOrderRepository([order])
    use_case = UpdateOrderNotes(orders)
    delivery = make_user(user_id=50, role=UserRole.DELIVERY_MANAGER, store_id=None)

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=delivery, order_id=30, notes="internal note")
