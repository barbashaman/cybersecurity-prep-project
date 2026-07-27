"""PR-safe SLO gates for auth, checkout, shipping, and order list paths."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from tests.performance.conftest import PerfTenant, assert_under_slo, seed_perf_tenant

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

pytestmark = [pytest.mark.performance, pytest.mark.performance_fast]

# Generous budgets keep CI/local runs stable across hardware variance.
_AUTH_LOGIN_SLO_SECONDS = 2.0
_CHECKOUT_SLO_SECONDS = 0.50
_SHIPPING_QUOTE_SLO_SECONDS = 0.10
_ORDER_LIST_SLO_SECONDS = 0.25


class _FastPasswordHasher:
    """Deterministic hasher for structural auth timing without Argon2 cost."""

    def hash_password(self, plain_password: str) -> str:
        return f"fast:{plain_password}"

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"fast:{plain_password}"


def test_authenticate_user_login_under_slo(db_session: Session) -> None:
    users = SqlAlchemyUserRepository(db_session)
    password = "Perf-Login-Password-9!"
    hasher = Argon2PasswordHasher()
    digest = hasher.hash_password(password)
    user = users.add(
        User(
            email="login-slo@perf.test",
            password_hash=digest,
            role=UserRole.CUSTOMER,
            full_name="Login SLO",
        )
    )
    assert user.id is not None

    use_case = AuthenticateUser(
        user_repository=users,
        password_hasher=hasher,
        token_service=JwtTokenService(
            secret="perf-test-secret",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )

    result, _timing = assert_under_slo(
        lambda: use_case.execute(email=user.email, password=password),
        label="AuthenticateUser.execute",
        max_median_seconds=_AUTH_LOGIN_SLO_SECONDS,
        iterations=3,
        warmup=1,
    )
    assert result.user_id == user.id
    assert result.access_token


def test_authenticate_user_structural_path_under_slo(db_session: Session) -> None:
    """Auth orchestration (lookup + token issue) without KDF cost."""
    users = SqlAlchemyUserRepository(db_session)
    password = "structural"
    hasher = _FastPasswordHasher()
    user = users.add(
        User(
            email="structural-login@perf.test",
            password_hash=hasher.hash_password(password),
            role=UserRole.ADMIN,
            full_name="Structural Login",
        )
    )
    assert user.id is not None
    use_case = AuthenticateUser(
        user_repository=users,
        password_hasher=hasher,
        token_service=JwtTokenService(
            secret="perf-test-secret",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )

    result, _timing = assert_under_slo(
        lambda: use_case.execute(email=user.email, password=password),
        label="AuthenticateUser.execute (fast hasher)",
        max_median_seconds=0.05,
        iterations=5,
        warmup=1,
    )
    assert result.role is UserRole.ADMIN


def test_place_order_checkout_under_slo(db_session: Session, perf_tenant: PerfTenant) -> None:
    assert perf_tenant.store.id is not None and perf_tenant.product.id is not None
    use_case = PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(db_session),
        product_repository=SqlAlchemyProductRepository(db_session),
        credit_repository=SqlAlchemyCreditRepository(db_session),
        coupon_repository=SqlAlchemyCouponRepository(db_session),
        store_repository=SqlAlchemyStoreRepository(db_session),
    )

    def _checkout() -> CheckoutResultView:
        return use_case.execute(
            actor=perf_tenant.customer,
            store_id=perf_tenant.store.id or 0,
            lines=[(perf_tenant.product.id or 0, 1)],
            shipping_address="1 Perf Checkout Way",
            customer_phone="+1-555-0300",
        )

    result, _timing = assert_under_slo(
        _checkout,
        label="PlaceOrder.execute",
        max_median_seconds=_CHECKOUT_SLO_SECONDS,
        iterations=3,
        warmup=1,
    )
    assert result.total_cents == 1000


def test_shipping_quote_under_slo(perf_tenant: PerfTenant) -> None:
    use_case = GetShippingQuote(MockShippingRateProvider())

    quote, _timing = assert_under_slo(
        lambda: use_case.execute(
            actor=perf_tenant.customer,
            destination_country="PT",
            parcel_weight_kg=1.25,
        ),
        label="GetShippingQuote.execute",
        max_median_seconds=_SHIPPING_QUOTE_SLO_SECONDS,
        iterations=5,
        warmup=1,
    )
    assert quote.amount_cents > 0
    assert quote.currency == "EUR"


def test_list_orders_under_slo_for_admin(db_session: Session) -> None:
    tenant = seed_perf_tenant(db_session, order_ready_stock=40)
    assert tenant.store.id is not None and tenant.product.id is not None
    placer = PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(db_session),
        product_repository=SqlAlchemyProductRepository(db_session),
        credit_repository=SqlAlchemyCreditRepository(db_session),
        coupon_repository=SqlAlchemyCouponRepository(db_session),
        store_repository=SqlAlchemyStoreRepository(db_session),
    )
    for index in range(20):
        placer.execute(
            actor=tenant.customer,
            store_id=tenant.store.id,
            lines=[(tenant.product.id, 1)],
            shipping_address=f"{index} List Perf Way",
        )

    listing = ListOrdersForStore(
        SqlAlchemyOrderRepository(db_session),
        SqlAlchemyStoreRepository(db_session),
    )
    views, _timing = assert_under_slo(
        lambda: listing.execute(actor=tenant.admin, store_id=tenant.store.id or 0),
        label="ListOrdersForStore.execute (admin)",
        max_median_seconds=_ORDER_LIST_SLO_SECONDS,
        iterations=5,
        warmup=1,
    )
    assert len(views) == 20
