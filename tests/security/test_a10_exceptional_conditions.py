"""Detection tests for OWASP A10 — Mishandling of Exceptional Conditions (iter-01).

These tests assert *secure* behaviour:
- unhandled errors must not leak stack traces to clients (even when DEBUG=true)
- invalid order-status transitions must be rejected (fail closed)

Against the deliberately vulnerable red-phase code they FAIL (red). After
remediation they PASS (green). They are intentionally outside the quality-gate
domain+toolkit subset so Phase 1b CI stays green until this suite is wired in.
"""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.application.use_cases.orders import UpdateOrderStatus
from ecommerce_backoffice_api.application.use_cases.products import ImportProductsFromCsv
from ecommerce_backoffice_api.domain.entities import Order, Product, Store, User
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import ConflictError
from ecommerce_backoffice_api.domain.order_status_transitions import (
    is_allowed_order_status_transition,
)
from ecommerce_backoffice_api.presentation.exception_handlers import (
    build_unhandled_error_response,
)

pytestmark = pytest.mark.security


class _FakeStoreRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    def get_by_id(self, store_id: int) -> Store | None:
        if self._store.id == store_id:
            return self._store
        return None

    def list_all(self) -> list[Store]:
        return [self._store]

    def add(self, store: Store) -> Store:
        return store


class _FakeProductRepository:
    def __init__(self) -> None:
        self._next_id = 1
        self.products: list[Product] = []

    def list_for_store(self, store_id: int) -> list[Product]:
        return [product for product in self.products if product.store_id == store_id]

    def get_by_id(self, product_id: int) -> Product | None:
        for product in self.products:
            if product.id == product_id:
                return product
        return None

    def add(self, product: Product) -> Product:
        product.id = self._next_id
        self._next_id += 1
        self.products.append(product)
        return product

    def save(self, product: Product) -> Product:
        return product


class _FakeOrderRepository:
    def __init__(self, order: Order) -> None:
        self._order = order

    def list_for_store(self, store_id: int) -> list[Order]:
        return [self._order] if self._order.store_id == store_id else []

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        if self._order.store_id == store_id and self._order.customer_user_id == customer_user_id:
            return [self._order]
        return []

    def get_by_id(self, order_id: int) -> Order | None:
        if self._order.id == order_id:
            return self._order
        return None

    def add(self, order: Order) -> Order:
        return order

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        if self._order.id != order_id:
            raise LookupError(order_id)
        self._order.status = status
        return self._order


def _admin() -> User:
    return User(
        id=1,
        email="admin@example.test",
        password_hash="unused",
        role=UserRole.ADMIN,
        full_name="Ada Admin",
        store_id=None,
    )


def _delivered_order() -> Order:
    return Order(
        id=42,
        store_id=1,
        customer_user_id=10,
        status=OrderStatus.DELIVERED,
        customer_email="customer@example.test",
        customer_full_name="Casey Customer",
        shipping_address="1 Demo Way",
    )


def test_debug_error_response_must_not_leak_stack_trace() -> None:
    """Secure: DEBUG error bodies must not expose Traceback / exception types."""
    try:
        raise KeyError("name")
    except KeyError as error:
        response = build_unhandled_error_response(error, debug=True)

    body = bytes(response.body).decode("utf-8")
    assert response.status_code == 500
    assert "Traceback" not in body
    assert "KeyError" not in body


def test_csv_import_exception_must_not_leak_stack_trace_markers() -> None:
    """Secure: forcing a CSV import exception must not yield traceback markers."""
    store = Store(id=1, name="Northwind Outfitters", owner_user_id=2)
    use_case = ImportProductsFromCsv(_FakeProductRepository(), _FakeStoreRepository(store))
    # Missing required columns → KeyError inside the vulnerable importer.
    malformed_csv = "title,cost\nbad-row,100\n"

    with pytest.raises(KeyError) as raised:
        use_case.execute(actor=_admin(), store_id=1, csv_text=malformed_csv)

    response = build_unhandled_error_response(raised.value, debug=True)
    body = bytes(response.body).decode("utf-8")
    assert "Traceback" not in body
    assert "KeyError" not in body


def test_csv_import_zero_division_must_not_leak_stack_trace_markers() -> None:
    """Secure: ZeroDivisionError during import must not leak stack frames."""
    store = Store(id=1, name="Northwind Outfitters", owner_user_id=2)
    use_case = ImportProductsFromCsv(_FakeProductRepository(), _FakeStoreRepository(store))
    zero_divisor_csv = (
        "name,description,price_cents,is_active,quantity_hint\n"
        "Broken Widget,forces division by zero,1999,true,0\n"
    )

    with pytest.raises(ZeroDivisionError) as raised:
        use_case.execute(actor=_admin(), store_id=1, csv_text=zero_divisor_csv)

    response = build_unhandled_error_response(raised.value, debug=True)
    body = bytes(response.body).decode("utf-8")
    assert "Traceback" not in body
    assert "ZeroDivisionError" not in body


def test_invalid_order_status_transition_must_be_rejected() -> None:
    """Secure: delivered → pending is illegal and must raise ConflictError."""
    assert not is_allowed_order_status_transition(OrderStatus.DELIVERED, OrderStatus.PENDING)

    order = _delivered_order()
    use_case = UpdateOrderStatus(_FakeOrderRepository(order))

    with pytest.raises(ConflictError):
        use_case.execute(actor=_admin(), order_id=42, status=OrderStatus.PENDING)

    # Secure path must leave the aggregate unchanged.
    assert order.status is OrderStatus.DELIVERED
