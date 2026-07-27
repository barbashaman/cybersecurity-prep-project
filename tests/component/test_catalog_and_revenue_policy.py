"""Component tests for catalog writes and revenue access policy."""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.application.use_cases.products import CreateProduct, ListProductsForStore
from ecommerce_backoffice_api.application.use_cases.revenue import GetStoreRevenue
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError
from tests.component.factories import make_order, make_product, make_store, make_user
from tests.component.fakes import FakeOrderRepository, FakeProductRepository, FakeStoreRepository

pytestmark = pytest.mark.component

STORE_A_PUBLIC = "8a1f3d7a-cf7e-4a27-a2e8-47142f5be7ac"
STORE_B_PUBLIC = "f8c7f0d9-2360-4f91-921a-1550c8e5b4b2"


def test_list_products_denies_cross_tenant_owner() -> None:
    stores = FakeStoreRepository(
        [
            make_store(store_id=1, public_id=STORE_A_PUBLIC),
            make_store(store_id=2, public_id=STORE_B_PUBLIC, owner_user_id=12),
        ]
    )
    products = FakeProductRepository([make_product(store_id=1)])
    use_case = ListProductsForStore(products, stores)
    foreign_owner = make_user(user_id=12, role=UserRole.STORE_OWNER, store_id=2)

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=foreign_owner, store_id=1)


def test_create_product_allowed_for_owning_owner_denied_for_customer() -> None:
    stores = FakeStoreRepository([make_store(store_id=1)])
    products = FakeProductRepository()
    use_case = CreateProduct(products, stores)

    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)
    with pytest.raises(AuthorizationError):
        use_case.execute(
            actor=customer,
            store_id=1,
            name="Denied",
            description="nope",
            price_cents=100,
        )

    owner = make_user(user_id=11, role=UserRole.STORE_OWNER, store_id=1)
    created = use_case.execute(
        actor=owner,
        store_id=1,
        name="Allowed",
        description="yes",
        price_cents=2500,
        stock_quantity=3,
    )
    assert created.name == "Allowed"
    assert created.stock_quantity == 3


def test_revenue_policy_blocks_customer_delivery_and_foreign_owner() -> None:
    stores = FakeStoreRepository(
        [
            make_store(store_id=1, public_id=STORE_A_PUBLIC, name="Store A", owner_user_id=11),
            make_store(store_id=2, public_id=STORE_B_PUBLIC, name="Store B", owner_user_id=12),
        ]
    )
    orders = FakeOrderRepository(
        [
            make_order(order_id=10, store_id=1, status=OrderStatus.CONFIRMED, quantity=2),
            make_order(order_id=11, store_id=1, status=OrderStatus.CANCELLED, quantity=1),
        ]
    )
    use_case = GetStoreRevenue(stores, orders)

    customer = make_user(user_id=201, role=UserRole.CUSTOMER, store_id=1)
    delivery = make_user(user_id=50, role=UserRole.DELIVERY_MANAGER, store_id=None)
    foreign_owner = make_user(user_id=12, role=UserRole.STORE_OWNER, store_id=2)

    for actor in (customer, delivery, foreign_owner):
        with pytest.raises(AuthorizationError):
            use_case.execute(actor=actor, store_public_id=STORE_A_PUBLIC)

    owner = make_user(user_id=11, role=UserRole.STORE_OWNER, store_id=1)
    view = use_case.execute(actor=owner, store_public_id=STORE_A_PUBLIC.upper())
    assert view.store_name == "Store A"
    assert view.total_orders == 2
    assert view.paid_orders == 1
    assert view.gross_revenue_cents == 2000
