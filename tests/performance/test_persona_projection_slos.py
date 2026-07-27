"""Role-sensitive performance scenarios where projection/query shape differs."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from tests.performance.conftest import (
    PerfTenant,
    assert_under_slo,
    measure_operation,
    seed_perf_tenant,
)

from ecommerce_backoffice_api.application.dto.orders import AnonymizedOrderView, OrderDetailView
from ecommerce_backoffice_api.application.use_cases.checkout import PlaceOrder
from ecommerce_backoffice_api.application.use_cases.orders import ListOrdersForStore
from ecommerce_backoffice_api.application.use_cases.shipping_rates import GetShippingQuote
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError
from ecommerce_backoffice_api.infrastructure.integrations.shipping import MockShippingRateProvider
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyCouponRepository,
    SqlAlchemyCreditRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStoreRepository,
)

pytestmark = [pytest.mark.performance, pytest.mark.performance_fast]

_ORDER_LIST_SLO_SECONDS = 0.30
_DENIED_AUTHZ_SLO_SECONDS = 0.05
_MAX_PROJECTION_RATIO = 4.0


def _place_orders(session: Session, *, count: int) -> tuple[PerfTenant, ListOrdersForStore]:
    tenant = seed_perf_tenant(session, order_ready_stock=count + 5)
    assert tenant.store.id is not None and tenant.product.id is not None
    placer = PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(session),
        product_repository=SqlAlchemyProductRepository(session),
        credit_repository=SqlAlchemyCreditRepository(session),
        coupon_repository=SqlAlchemyCouponRepository(session),
        store_repository=SqlAlchemyStoreRepository(session),
    )
    for index in range(count):
        placer.execute(
            actor=tenant.customer,
            store_id=tenant.store.id,
            lines=[(tenant.product.id, 1)],
            shipping_address=f"{index} Persona Perf Way",
        )
    return tenant, ListOrdersForStore(
        SqlAlchemyOrderRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def test_admin_and_delivery_manager_list_orders_under_slo(db_session: Session) -> None:
    tenant, listing = _place_orders(db_session, count=25)
    store_id = tenant.store.id
    assert store_id is not None

    admin_views, admin_timing = assert_under_slo(
        lambda: listing.execute(actor=tenant.admin, store_id=store_id),
        label="ListOrdersForStore (admin full projection)",
        max_median_seconds=_ORDER_LIST_SLO_SECONDS,
        iterations=5,
        warmup=1,
    )
    delivery_views, delivery_timing = assert_under_slo(
        lambda: listing.execute(actor=tenant.delivery, store_id=store_id),
        label="ListOrdersForStore (delivery anonymized projection)",
        max_median_seconds=_ORDER_LIST_SLO_SECONDS,
        iterations=5,
        warmup=1,
    )

    assert len(admin_views) == 25
    assert len(delivery_views) == 25
    assert all(isinstance(view, OrderDetailView) for view in admin_views)
    assert all(isinstance(view, AnonymizedOrderView) for view in delivery_views)

    # Anonymization must not explode latency relative to the full projection.
    ratio = delivery_timing.median_seconds / max(admin_timing.median_seconds, 1e-6)
    assert ratio <= _MAX_PROJECTION_RATIO, (
        f"Delivery projection median {delivery_timing.median_seconds:.4f}s is "
        f"{ratio:.1f}x admin median {admin_timing.median_seconds:.4f}s "
        f"(limit {_MAX_PROJECTION_RATIO}x)"
    )


def test_customer_order_list_filters_own_orders_under_slo(db_session: Session) -> None:
    tenant, listing = _place_orders(db_session, count=15)
    store_id = tenant.store.id
    assert store_id is not None

    views, _timing = assert_under_slo(
        lambda: listing.execute(actor=tenant.customer, store_id=store_id),
        label="ListOrdersForStore (customer filtered)",
        max_median_seconds=_ORDER_LIST_SLO_SECONDS,
        iterations=5,
        warmup=1,
    )
    assert len(views) == 15
    assert all(isinstance(view, OrderDetailView) for view in views)


def test_shipping_quote_denial_for_delivery_manager_is_fast(db_session: Session) -> None:
    tenant = seed_perf_tenant(db_session, order_ready_stock=1)
    use_case = GetShippingQuote(MockShippingRateProvider())

    def _denied() -> None:
        with pytest.raises(AuthorizationError):
            use_case.execute(
                actor=tenant.delivery,
                destination_country="PT",
                parcel_weight_kg=1.0,
            )

    _result, timing = measure_operation(_denied, iterations=5, warmup=1)
    assert timing.median_seconds <= _DENIED_AUTHZ_SLO_SECONDS, (
        f"Denied shipping quote median {timing.median_seconds:.4f}s exceeded "
        f"SLO {_DENIED_AUTHZ_SLO_SECONDS:.4f}s"
    )
