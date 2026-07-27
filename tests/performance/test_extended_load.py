"""Extended performance profile: larger datasets and repeated critical paths.

Not required on PR CI. Run with::

    pytest tests/performance -m performance_extended
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from tests.performance.conftest import assert_under_slo, seed_perf_tenant

from ecommerce_backoffice_api.application.dto.checkout import CheckoutResultView
from ecommerce_backoffice_api.application.use_cases.authentication import AuthenticateUser
from ecommerce_backoffice_api.application.use_cases.checkout import PlaceOrder
from ecommerce_backoffice_api.application.use_cases.orders import ListOrdersForStore
from ecommerce_backoffice_api.application.use_cases.shipping_rates import GetShippingQuote
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.infrastructure.integrations.shipping import MockShippingRateProvider
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyCouponRepository,
    SqlAlchemyCreditRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStoreRepository,
    SqlAlchemyUserRepository,
)
from ecommerce_backoffice_api.infrastructure.security.jwt_token_service import JwtTokenService
from ecommerce_backoffice_api.infrastructure.security.password_hasher import Argon2PasswordHasher

pytestmark = [pytest.mark.performance, pytest.mark.performance_extended]

_EXTENDED_ORDER_COUNT = 120
_EXTENDED_LIST_SLO_SECONDS = 1.50
_EXTENDED_CHECKOUT_BURST_SLO_SECONDS = 0.75
_EXTENDED_AUTH_BURST_SLO_SECONDS = 2.50
_EXTENDED_SHIPPING_BURST_SLO_SECONDS = 0.25


def test_list_orders_scales_for_admin_and_delivery(db_session: Session) -> None:
    tenant = seed_perf_tenant(db_session, order_ready_stock=_EXTENDED_ORDER_COUNT + 10)
    assert tenant.store.id is not None and tenant.product.id is not None
    placer = PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(db_session),
        product_repository=SqlAlchemyProductRepository(db_session),
        credit_repository=SqlAlchemyCreditRepository(db_session),
        coupon_repository=SqlAlchemyCouponRepository(db_session),
        store_repository=SqlAlchemyStoreRepository(db_session),
    )
    for index in range(_EXTENDED_ORDER_COUNT):
        placer.execute(
            actor=tenant.customer,
            store_id=tenant.store.id,
            lines=[(tenant.product.id, 1)],
            shipping_address=f"{index} Extended Perf Way",
        )

    listing = ListOrdersForStore(
        SqlAlchemyOrderRepository(db_session),
        SqlAlchemyStoreRepository(db_session),
    )
    store_id = tenant.store.id

    admin_views, _admin_timing = assert_under_slo(
        lambda: listing.execute(actor=tenant.admin, store_id=store_id),
        label=f"ListOrdersForStore admin ({_EXTENDED_ORDER_COUNT} orders)",
        max_median_seconds=_EXTENDED_LIST_SLO_SECONDS,
        iterations=3,
        warmup=1,
    )
    delivery_views, _delivery_timing = assert_under_slo(
        lambda: listing.execute(actor=tenant.delivery, store_id=store_id),
        label=f"ListOrdersForStore delivery ({_EXTENDED_ORDER_COUNT} orders)",
        max_median_seconds=_EXTENDED_LIST_SLO_SECONDS,
        iterations=3,
        warmup=1,
    )
    assert len(admin_views) == _EXTENDED_ORDER_COUNT
    assert len(delivery_views) == _EXTENDED_ORDER_COUNT


def test_checkout_burst_under_slo(db_session: Session) -> None:
    tenant = seed_perf_tenant(db_session, order_ready_stock=40)
    assert tenant.store.id is not None and tenant.product.id is not None
    use_case = PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(db_session),
        product_repository=SqlAlchemyProductRepository(db_session),
        credit_repository=SqlAlchemyCreditRepository(db_session),
        coupon_repository=SqlAlchemyCouponRepository(db_session),
        store_repository=SqlAlchemyStoreRepository(db_session),
    )

    def _checkout() -> CheckoutResultView:
        return use_case.execute(
            actor=tenant.customer,
            store_id=tenant.store.id or 0,
            lines=[(tenant.product.id or 0, 1)],
            shipping_address="Burst Checkout Way",
            customer_phone="+1-555-0400",
        )

    result, _timing = assert_under_slo(
        _checkout,
        label="PlaceOrder.execute burst",
        max_median_seconds=_EXTENDED_CHECKOUT_BURST_SLO_SECONDS,
        iterations=10,
        warmup=2,
    )
    assert result.total_cents == 1000


def test_shipping_quote_burst_under_slo(db_session: Session) -> None:
    tenant = seed_perf_tenant(db_session, order_ready_stock=1)
    use_case = GetShippingQuote(MockShippingRateProvider())

    quote, _timing = assert_under_slo(
        lambda: use_case.execute(
            actor=tenant.customer,
            destination_country="PT",
            parcel_weight_kg=2.0,
        ),
        label="GetShippingQuote.execute burst",
        max_median_seconds=_EXTENDED_SHIPPING_BURST_SLO_SECONDS,
        iterations=20,
        warmup=2,
    )
    assert quote.currency == "EUR"


def test_argon2_login_burst_under_slo(db_session: Session) -> None:
    users = SqlAlchemyUserRepository(db_session)
    password = "Extended-Login-Password-9!"
    hasher = Argon2PasswordHasher()
    user = users.add(
        User(
            email="extended-login@perf.test",
            password_hash=hasher.hash_password(password),
            role=UserRole.STORE_OWNER,
            full_name="Extended Login",
        )
    )
    assert user.id is not None
    use_case = AuthenticateUser(
        user_repository=users,
        password_hasher=hasher,
        token_service=JwtTokenService(
            secret="perf-extended-secret",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )

    result, _timing = assert_under_slo(
        lambda: use_case.execute(email=user.email, password=password),
        label="AuthenticateUser.execute Argon2 burst",
        max_median_seconds=_EXTENDED_AUTH_BURST_SLO_SECONDS,
        iterations=5,
        warmup=1,
    )
    assert result.user_id == user.id
