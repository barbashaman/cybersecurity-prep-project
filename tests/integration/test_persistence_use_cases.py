"""Integration tests: use cases + SQLAlchemy persistence (no HTTP)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from ecommerce_backoffice_api.application.dto.orders import AnonymizedOrderView, OrderDetailView
from ecommerce_backoffice_api.application.use_cases.checkout import PlaceOrder
from ecommerce_backoffice_api.application.use_cases.orders import ListOrdersForStore
from ecommerce_backoffice_api.application.use_cases.revenue import GetStoreRevenue
from ecommerce_backoffice_api.application.use_cases.shipping_rates import GetShippingQuote
from ecommerce_backoffice_api.domain.entities import CustomerCredit, Product, Store, User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, ConflictError
from ecommerce_backoffice_api.infrastructure.integrations.shipping import MockShippingRateProvider
from ecommerce_backoffice_api.infrastructure.persistence.models import UserModel
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyCouponRepository,
    SqlAlchemyCreditRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStoreRepository,
    SqlAlchemyUserRepository,
)

pytestmark = pytest.mark.integration
pytest_plugins = ["tests.database.conftest"]


def _seed_tenant(session: Session) -> tuple[User, User, Store, Product]:
    users = SqlAlchemyUserRepository(session)
    stores = SqlAlchemyStoreRepository(session)
    products = SqlAlchemyProductRepository(session)
    credits = SqlAlchemyCreditRepository(session)

    owner = users.add(
        User(
            email="owner@int.test",
            password_hash="h",
            role=UserRole.STORE_OWNER,
            full_name="Owner",
        )
    )
    store = stores.add(
        Store(name="Integration Store", owner_user_id=owner.id, public_id=str(uuid.uuid4()))
    )
    assert owner.id is not None and store.id is not None
    owner_model = session.get(UserModel, owner.id)
    assert owner_model is not None
    owner_model.store_id = store.id
    owner.store_id = store.id

    customer = users.add(
        User(
            email="customer@int.test",
            password_hash="h",
            role=UserRole.CUSTOMER,
            full_name="Customer",
            store_id=store.id,
        )
    )
    assert customer.id is not None
    credits.save(CustomerCredit(user_id=customer.id, balance_cents=50_000))
    product = products.add(
        Product(
            store_id=store.id,
            name="Widget",
            description="demo",
            price_cents=1000,
            stock_quantity=5,
        )
    )
    return owner, customer, store, product


def test_place_order_persists_and_decrements_stock(db_session: Session) -> None:
    _, customer, store, product = _seed_tenant(db_session)
    assert store.id is not None and product.id is not None

    use_case = PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(db_session),
        product_repository=SqlAlchemyProductRepository(db_session),
        credit_repository=SqlAlchemyCreditRepository(db_session),
        coupon_repository=SqlAlchemyCouponRepository(db_session),
        store_repository=SqlAlchemyStoreRepository(db_session),
    )
    result = use_case.execute(
        actor=customer,
        store_id=store.id,
        lines=[(product.id, 2)],
        shipping_address="99 Integration Way",
        customer_phone="+1-555-0200",
    )
    assert result.order.id is not None
    assert result.total_cents == 2000

    refreshed = SqlAlchemyProductRepository(db_session).get_by_id(product.id)
    assert refreshed is not None
    assert refreshed.stock_quantity == 3

    orders = SqlAlchemyOrderRepository(db_session).list_for_store(store.id)
    assert len(orders) == 1
    assert orders[0].customer_phone == "+1-555-0200"


def test_list_orders_persona_visibility_with_persisted_data(db_session: Session) -> None:
    owner, customer, store, product = _seed_tenant(db_session)
    assert store.id is not None and product.id is not None

    PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(db_session),
        product_repository=SqlAlchemyProductRepository(db_session),
        credit_repository=SqlAlchemyCreditRepository(db_session),
        coupon_repository=SqlAlchemyCouponRepository(db_session),
        store_repository=SqlAlchemyStoreRepository(db_session),
    ).execute(
        actor=customer,
        store_id=store.id,
        lines=[(product.id, 1)],
        shipping_address="1 Persona Way",
    )

    users = SqlAlchemyUserRepository(db_session)
    other_customer = users.add(
        User(
            email="other@int.test",
            password_hash="h",
            role=UserRole.CUSTOMER,
            full_name="Other",
            store_id=store.id,
        )
    )
    delivery = users.add(
        User(
            email="delivery@int.test",
            password_hash="h",
            role=UserRole.DELIVERY_MANAGER,
            full_name="Delivery",
            store_id=None,
        )
    )

    listing = ListOrdersForStore(
        SqlAlchemyOrderRepository(db_session),
        SqlAlchemyStoreRepository(db_session),
    )
    owner_views = listing.execute(actor=owner, store_id=store.id)
    assert len(owner_views) == 1
    assert isinstance(owner_views[0], OrderDetailView)
    assert owner_views[0].customer_email == customer.email

    customer_views = listing.execute(actor=customer, store_id=store.id)
    assert len(customer_views) == 1

    other_views = listing.execute(actor=other_customer, store_id=store.id)
    assert other_views == []

    delivery_views = listing.execute(actor=delivery, store_id=store.id)
    assert len(delivery_views) == 1
    assert isinstance(delivery_views[0], AnonymizedOrderView)


def test_revenue_tenant_boundary_against_persisted_orders(db_session: Session) -> None:
    owner, customer, store, product = _seed_tenant(db_session)
    assert store.id is not None and product.id is not None and store.public_id is not None

    PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(db_session),
        product_repository=SqlAlchemyProductRepository(db_session),
        credit_repository=SqlAlchemyCreditRepository(db_session),
        coupon_repository=SqlAlchemyCouponRepository(db_session),
        store_repository=SqlAlchemyStoreRepository(db_session),
    ).execute(
        actor=customer,
        store_id=store.id,
        lines=[(product.id, 1)],
        shipping_address="1 Revenue Way",
    )

    foreign_owner = SqlAlchemyUserRepository(db_session).add(
        User(
            email="foreign@int.test",
            password_hash="h",
            role=UserRole.STORE_OWNER,
            full_name="Foreign",
            store_id=None,
        )
    )
    foreign_owner.store_id = 999
    use_case = GetStoreRevenue(
        SqlAlchemyStoreRepository(db_session),
        SqlAlchemyOrderRepository(db_session),
    )
    allowed = use_case.execute(actor=owner, store_public_id=store.public_id)
    assert allowed.total_orders == 1
    assert allowed.gross_revenue_cents == 1000

    with pytest.raises(AuthorizationError):
        use_case.execute(actor=foreign_owner, store_public_id=store.public_id)


def test_shipping_quote_integration_with_mock_provider() -> None:
    use_case = GetShippingQuote(MockShippingRateProvider())
    customer = User(
        id=1,
        email="c@int.test",
        password_hash="h",
        role=UserRole.CUSTOMER,
        full_name="C",
        store_id=1,
    )
    quote = use_case.execute(actor=customer, destination_country="PT", parcel_weight_kg=1.0)
    assert quote.currency == "EUR"
    assert quote.amount_cents == 750

    delivery = User(
        id=2,
        email="d@int.test",
        password_hash="h",
        role=UserRole.DELIVERY_MANAGER,
        full_name="D",
        store_id=None,
    )
    with pytest.raises(AuthorizationError):
        use_case.execute(actor=delivery, destination_country="PT", parcel_weight_kg=1.0)

    with pytest.raises(ConflictError):
        use_case.execute(actor=customer, destination_country="PT", parcel_weight_kg=0)
