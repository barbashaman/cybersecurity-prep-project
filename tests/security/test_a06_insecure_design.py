"""Detection tests for OWASP A06 — Insecure Design (iter-05).

These tests assert *secure* behaviour:
- a coupon cannot be reused after it has been redeemed
- checkout rejects non-positive line quantities
- ordering beyond available stock is rejected (atomic stock invariant)

Against the deliberately vulnerable red-phase code they FAIL (red). After
remediation they PASS (green). They are intentionally outside the quality-gate
domain+toolkit subset so Phase 1b CI stays green until this suite is wired in.
"""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.application.use_cases.checkout import PlaceOrder
from ecommerce_backoffice_api.domain.entities import (
    Coupon,
    CouponRedemption,
    CustomerCredit,
    Order,
    Product,
    Store,
    User,
)
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import ConflictError

pytestmark = pytest.mark.security


class _FakeStoreRepository:
    def __init__(self, store: Store) -> None:
        self._store = store

    def list_all(self) -> list[Store]:
        return [self._store]

    def get_by_id(self, store_id: int) -> Store | None:
        return self._store if self._store.id == store_id else None

    def add(self, store: Store) -> Store:
        return store


class _FakeProductRepository:
    def __init__(self, product: Product) -> None:
        self.product = product

    def list_for_store(self, store_id: int) -> list[Product]:
        return [self.product] if self.product.store_id == store_id else []

    def get_by_id(self, product_id: int) -> Product | None:
        return self.product if self.product.id == product_id else None

    def add(self, product: Product) -> Product:
        return product

    def save(self, product: Product) -> Product:
        self.product = product
        return product


class _FakeOrderRepository:
    def __init__(self) -> None:
        self.orders: list[Order] = []
        self._next_id = 1

    def list_for_store(self, store_id: int) -> list[Order]:
        return [order for order in self.orders if order.store_id == store_id]

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        return [
            order
            for order in self.orders
            if order.store_id == store_id and order.customer_user_id == customer_user_id
        ]

    def get_by_id(self, order_id: int) -> Order | None:
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def add(self, order: Order) -> Order:
        order.id = self._next_id
        self._next_id += 1
        line_id = 1
        for line in order.lines:
            line.id = line_id
            line.order_id = order.id
            line_id += 1
        self.orders.append(order)
        return order

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        order = self.get_by_id(order_id)
        assert order is not None
        order.status = status
        return order


class _FakeCreditRepository:
    def __init__(self, credit: CustomerCredit) -> None:
        self.credit = credit

    def get_for_user(self, user_id: int) -> CustomerCredit | None:
        return self.credit if self.credit.user_id == user_id else None

    def save(self, credit: CustomerCredit) -> CustomerCredit:
        self.credit = credit
        if self.credit.id is None:
            self.credit.id = 1
        return self.credit


class _FakeCouponRepository:
    def __init__(self, coupon: Coupon) -> None:
        self.coupon = coupon
        self.redemptions: list[CouponRedemption] = []

    def add(self, coupon: Coupon) -> Coupon:
        self.coupon = coupon
        if self.coupon.id is None:
            self.coupon.id = 1
        return self.coupon

    def get_by_code(self, store_id: int, code: str) -> Coupon | None:
        if (
            self.coupon.store_id == store_id
            and self.coupon.code == code.strip().upper()
            and self.coupon.is_active
        ):
            return self.coupon
        return None

    def record_redemption(self, redemption: CouponRedemption) -> CouponRedemption:
        redemption.id = len(self.redemptions) + 1
        self.redemptions.append(redemption)
        return redemption

    def has_been_redeemed(self, coupon_id: int) -> bool:
        return any(item.coupon_id == coupon_id for item in self.redemptions)


def _customer() -> User:
    return User(
        id=11,
        email="customer1@example.test",
        password_hash="hashed:ChangeMeDemoOnly!",
        role=UserRole.CUSTOMER,
        full_name="Carla Customer",
        store_id=1,
    )


def _store() -> Store:
    return Store(id=1, name="Northwind Outfitters", owner_user_id=2)


def _product(*, stock_quantity: int) -> Product:
    return Product(
        id=101,
        store_id=1,
        name="NW Trail Backpack",
        description="Durable daypack.",
        price_cents=1000,
        is_active=True,
        stock_quantity=stock_quantity,
    )


def _coupon() -> Coupon:
    return Coupon(id=7, store_id=1, code="SAVE10", discount_percent=10, is_active=True)


def _place_order(
    *,
    stock_quantity: int = 10,
    balance_cents: int = 100_000,
) -> tuple[PlaceOrder, _FakeProductRepository, _FakeCouponRepository, _FakeOrderRepository]:
    product_repo = _FakeProductRepository(_product(stock_quantity=stock_quantity))
    coupon_repo = _FakeCouponRepository(_coupon())
    order_repo = _FakeOrderRepository()
    use_case = PlaceOrder(
        order_repository=order_repo,
        product_repository=product_repo,
        credit_repository=_FakeCreditRepository(
            CustomerCredit(user_id=11, balance_cents=balance_cents, id=1)
        ),
        coupon_repository=coupon_repo,
        store_repository=_FakeStoreRepository(_store()),
    )
    return use_case, product_repo, coupon_repo, order_repo


def test_coupon_must_not_be_reusable_after_redemption() -> None:
    """Secure: the same coupon code must fail on a second checkout."""
    use_case, _product_repo, coupon_repo, _order_repo = _place_order(stock_quantity=5)

    first = use_case.execute(
        actor=_customer(),
        store_id=1,
        lines=[(101, 1)],
        shipping_address="12 Pine Street",
        coupon_code="SAVE10",
    )
    assert first.coupon_code == "SAVE10"
    assert first.discount_cents > 0
    assert coupon_repo.coupon.id is not None

    with pytest.raises(ConflictError, match="(?i)redeem|reuse|already"):
        use_case.execute(
            actor=_customer(),
            store_id=1,
            lines=[(101, 1)],
            shipping_address="12 Pine Street",
            coupon_code="SAVE10",
        )

    # Secure remediation must leave a single redemption ledger entry.
    assert coupon_repo.has_been_redeemed(coupon_repo.coupon.id)
    assert len(coupon_repo.redemptions) == 1


def test_checkout_must_reject_negative_quantity() -> None:
    """Secure: non-positive line quantities must be rejected as a domain conflict."""
    use_case, product_repo, _coupon_repo, order_repo = _place_order(stock_quantity=5)
    initial_stock = product_repo.product.stock_quantity

    with pytest.raises(ConflictError, match="(?i)quantity"):
        use_case.execute(
            actor=_customer(),
            store_id=1,
            lines=[(101, -2)],
            shipping_address="12 Pine Street",
        )

    assert order_repo.orders == []
    assert product_repo.product.stock_quantity == initial_stock


def test_checkout_must_reject_ordering_beyond_stock() -> None:
    """Secure: a second checkout for the last unit must fail (no oversell)."""
    use_case, product_repo, _coupon_repo, order_repo = _place_order(stock_quantity=1)

    first = use_case.execute(
        actor=_customer(),
        store_id=1,
        lines=[(101, 1)],
        shipping_address="12 Pine Street",
    )
    assert first.order.id is not None
    assert product_repo.product.stock_quantity == 0

    with pytest.raises(ConflictError, match="(?i)stock|inventory|available"):
        use_case.execute(
            actor=_customer(),
            store_id=1,
            lines=[(101, 1)],
            shipping_address="12 Pine Street",
        )

    assert len(order_repo.orders) == 1
    assert product_repo.product.stock_quantity == 0
