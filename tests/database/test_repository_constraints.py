"""Repository/model constraint and mapping round-trip tests (SQLite)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ecommerce_backoffice_api.domain.entities import (
    Coupon,
    CustomerCredit,
    Order,
    OrderLine,
    Product,
    Store,
    User,
)
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.infrastructure.persistence.models import StoreModel, UserModel
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyCouponRepository,
    SqlAlchemyCreditRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStoreRepository,
    SqlAlchemyUserRepository,
)

pytestmark = pytest.mark.database


def _seed_owner_and_store(session: Session) -> tuple[User, Store]:
    users = SqlAlchemyUserRepository(session)
    stores = SqlAlchemyStoreRepository(session)
    owner = users.add(
        User(
            email="owner@db.test",
            password_hash="hash",
            role=UserRole.STORE_OWNER,
            full_name="Owner",
        )
    )
    store = stores.add(
        Store(
            name="DB Store",
            owner_user_id=owner.id,
            public_id=str(uuid.uuid4()),
        )
    )
    assert owner.id is not None
    owner.store_id = store.id
    model = session.get(UserModel, owner.id)
    assert model is not None
    model.store_id = store.id
    session.flush()
    return owner, store


def test_store_public_id_round_trip_and_case_insensitive_lookup(db_session: Session) -> None:
    _, store = _seed_owner_and_store(db_session)
    assert store.public_id is not None
    stores = SqlAlchemyStoreRepository(db_session)

    found = stores.get_by_public_id(store.public_id.upper())
    assert found is not None
    assert found.id == store.id
    assert found.public_id == store.public_id.lower()


def test_store_public_id_unique_constraint(db_session: Session) -> None:
    public_id = str(uuid.uuid4())
    db_session.add(StoreModel(public_id=public_id, name="A"))
    db_session.flush()
    db_session.add(StoreModel(public_id=public_id, name="B"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_user_email_unique_constraint(db_session: Session) -> None:
    db_session.add(
        UserModel(
            email="dup@db.test",
            password_hash="h",
            role=UserRole.CUSTOMER.value,
            full_name="One",
        )
    )
    db_session.flush()
    db_session.add(
        UserModel(
            email="dup@db.test",
            password_hash="h",
            role=UserRole.CUSTOMER.value,
            full_name="Two",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_product_and_order_mapping_round_trip(db_session: Session) -> None:
    owner, store = _seed_owner_and_store(db_session)
    assert store.id is not None and owner.id is not None

    products = SqlAlchemyProductRepository(db_session)
    product = products.add(
        Product(
            store_id=store.id,
            name="Gadget",
            description="desc",
            price_cents=1500,
            stock_quantity=4,
        )
    )
    assert product.id is not None

    customers = SqlAlchemyUserRepository(db_session)
    customer = customers.add(
        User(
            email="buyer@db.test",
            password_hash="h",
            role=UserRole.CUSTOMER,
            full_name="Buyer",
            store_id=store.id,
        )
    )
    assert customer.id is not None

    orders = SqlAlchemyOrderRepository(db_session)
    order = orders.add(
        Order(
            store_id=store.id,
            customer_user_id=customer.id,
            status=OrderStatus.PENDING,
            customer_email=customer.email,
            customer_full_name=customer.full_name,
            shipping_address="1 DB Lane",
            customer_phone="+1-555-0199",
            lines=[
                OrderLine(
                    product_id=product.id,
                    quantity=2,
                    unit_price_cents=product.price_cents,
                )
            ],
        )
    )
    assert order.id is not None
    loaded = orders.get_by_id(order.id)
    assert loaded is not None
    assert loaded.customer_phone == "+1-555-0199"
    assert len(loaded.lines) == 1
    assert loaded.lines[0].quantity == 2


def test_coupon_store_code_unique_and_credit_round_trip(db_session: Session) -> None:
    _, store = _seed_owner_and_store(db_session)
    assert store.id is not None
    coupons = SqlAlchemyCouponRepository(db_session)
    first = coupons.add(
        Coupon(store_id=store.id, code="SAVE10", discount_percent=10, is_active=True)
    )
    assert first.id is not None
    with pytest.raises(IntegrityError):
        coupons.add(Coupon(store_id=store.id, code="SAVE10", discount_percent=20, is_active=True))
    db_session.rollback()

    # Re-seed after rollback for credit path.
    _owner, store = _seed_owner_and_store(db_session)
    customers = SqlAlchemyUserRepository(db_session)
    customer = customers.add(
        User(
            email="credit@db.test",
            password_hash="h",
            role=UserRole.CUSTOMER,
            full_name="Credit",
            store_id=store.id,
        )
    )
    assert customer.id is not None
    credits = SqlAlchemyCreditRepository(db_session)
    saved = credits.save(CustomerCredit(user_id=customer.id, balance_cents=2500))
    loaded = credits.get_for_user(customer.id)
    assert loaded is not None
    assert loaded.balance_cents == 2500
    assert saved.id == loaded.id
