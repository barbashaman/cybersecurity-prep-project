"""Component tests for checkout invariants (stock, coupons, credits, personas)."""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.application.use_cases.checkout import (
    ApplyCouponToOrder,
    CreateCoupon,
    GrantCredits,
    PlaceOrder,
)
from ecommerce_backoffice_api.domain.entities import CustomerCredit
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, ConflictError
from tests.component.factories import (
    make_coupon,
    make_order,
    make_product,
    make_store,
    make_user,
)
from tests.component.fakes import (
    FakeCouponRepository,
    FakeCreditRepository,
    FakeOrderRepository,
    FakeProductRepository,
    FakeStoreRepository,
)

pytestmark = pytest.mark.component


def _place_order_use_case(
    *,
    products: FakeProductRepository,
    credits: FakeCreditRepository,
    coupons: FakeCouponRepository | None = None,
    orders: FakeOrderRepository | None = None,
    stores: FakeStoreRepository | None = None,
) -> PlaceOrder:
    return PlaceOrder(
        order_repository=orders or FakeOrderRepository(),
        product_repository=products,
        credit_repository=credits,
        coupon_repository=coupons or FakeCouponRepository(),
        store_repository=stores or FakeStoreRepository([make_store()]),
    )


def test_place_order_rejects_non_customer_and_foreign_store_customer() -> None:
    products = FakeProductRepository([make_product(stock_quantity=5)])
    credits = FakeCreditRepository([CustomerCredit(user_id=201, balance_cents=50_000)])
    use_case = _place_order_use_case(products=products, credits=credits)

    owner = make_user(user_id=11, role=UserRole.STORE_OWNER, store_id=1)
    with pytest.raises(AuthorizationError):
        use_case.execute(
            actor=owner,
            store_id=1,
            lines=[(1, 1)],
            shipping_address="1 Demo Way",
        )

    foreign_customer = make_user(user_id=202, role=UserRole.CUSTOMER, store_id=2)
    with pytest.raises(AuthorizationError):
        use_case.execute(
            actor=foreign_customer,
            store_id=1,
            lines=[(1, 1)],
            shipping_address="1 Demo Way",
        )


def test_place_order_rejects_non_positive_quantity() -> None:
    products = FakeProductRepository([make_product(stock_quantity=5)])
    credits = FakeCreditRepository([CustomerCredit(user_id=201, balance_cents=50_000)])
    use_case = _place_order_use_case(products=products, credits=credits)
    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)

    with pytest.raises(ConflictError, match="positive"):
        use_case.execute(
            actor=customer,
            store_id=1,
            lines=[(1, 0)],
            shipping_address="1 Demo Way",
        )


def test_place_order_rejects_oversell_and_decrements_stock_on_success() -> None:
    product = make_product(stock_quantity=2, price_cents=500)
    products = FakeProductRepository([product])
    credits = FakeCreditRepository([CustomerCredit(user_id=201, balance_cents=50_000)])
    use_case = _place_order_use_case(products=products, credits=credits)
    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)

    with pytest.raises(ConflictError, match="Insufficient stock"):
        use_case.execute(
            actor=customer,
            store_id=1,
            lines=[(1, 3)],
            shipping_address="1 Demo Way",
        )

    result = use_case.execute(
        actor=customer,
        store_id=1,
        lines=[(1, 2)],
        shipping_address="1 Demo Way",
    )
    assert result.total_cents == 1000
    updated = products.get_by_id(1)
    assert updated is not None
    assert updated.stock_quantity == 0


def test_coupon_cannot_be_replayed_after_redemption() -> None:
    product = make_product(stock_quantity=10, price_cents=1000)
    products = FakeProductRepository([product])
    credits = FakeCreditRepository([CustomerCredit(user_id=201, balance_cents=50_000)])
    coupons = FakeCouponRepository([make_coupon(code="SAVE10", discount_percent=10)])
    use_case = _place_order_use_case(products=products, credits=credits, coupons=coupons)
    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)

    first = use_case.execute(
        actor=customer,
        store_id=1,
        lines=[(1, 1)],
        shipping_address="1 Demo Way",
        coupon_code="save10",
    )
    assert first.discount_cents == 100
    assert first.total_cents == 900

    with pytest.raises(ConflictError, match="already been redeemed"):
        use_case.execute(
            actor=customer,
            store_id=1,
            lines=[(1, 1)],
            shipping_address="1 Demo Way",
            coupon_code="SAVE10",
        )


def test_apply_coupon_to_order_rejects_replay() -> None:
    order = make_order(order_id=50, quantity=2, unit_price_cents=1000)
    orders = FakeOrderRepository([order])
    coupons = FakeCouponRepository([make_coupon(code="REPLAY", discount_percent=20)])
    use_case = ApplyCouponToOrder(orders, coupons)
    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)

    first = use_case.execute(actor=customer, order_id=50, coupon_code="REPLAY")
    assert first.discount_cents == 400

    with pytest.raises(ConflictError, match="already been redeemed"):
        use_case.execute(actor=customer, order_id=50, coupon_code="REPLAY")


def test_place_order_idempotency_key_returns_cached_result() -> None:
    product = make_product(stock_quantity=5, price_cents=1000)
    products = FakeProductRepository([product])
    credits = FakeCreditRepository([CustomerCredit(user_id=201, balance_cents=50_000)])
    orders = FakeOrderRepository()
    use_case = _place_order_use_case(products=products, credits=credits, orders=orders)
    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)

    first = use_case.execute(
        actor=customer,
        store_id=1,
        lines=[(1, 1)],
        shipping_address="1 Demo Way",
        idempotency_key="checkout-1",
    )
    second = use_case.execute(
        actor=customer,
        store_id=1,
        lines=[(1, 1)],
        shipping_address="1 Demo Way",
        idempotency_key="checkout-1",
    )
    assert first.order.id == second.order.id
    assert len(orders.list_for_store(1)) == 1
    remaining = products.get_by_id(1)
    assert remaining is not None
    assert remaining.stock_quantity == 4


def test_create_coupon_is_tenant_scoped_for_store_owner() -> None:
    stores = FakeStoreRepository([make_store(store_id=1), make_store(store_id=2, public_id="bbbb")])
    coupons = FakeCouponRepository()
    use_case = CreateCoupon(coupons, stores)
    owner = make_user(user_id=12, role=UserRole.STORE_OWNER, store_id=1)

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=owner, store_id=2, code="X", discount_percent=10)

    created = use_case.execute(actor=owner, store_id=1, code="own", discount_percent=15)
    assert created.code == "OWN"
    assert created.discount_percent == 15


def test_grant_credits_customer_self_only_and_owner_denied() -> None:
    credits = FakeCreditRepository()
    use_case = GrantCredits(credits)
    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)
    owner = make_user(user_id=11, role=UserRole.STORE_OWNER, store_id=1)

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=owner, user_id=201, amount_cents=100)

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=customer, user_id=999, amount_cents=100)

    view = use_case.execute(actor=customer, user_id=201, amount_cents=250)
    assert view.balance_cents == 250
