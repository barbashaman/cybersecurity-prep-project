"""Shared fixtures and timing helpers for performance SLO suites.

Performance tests reuse the isolated SQLite fixtures from ``tests.database`` so
they remain deterministic and do not require a running HTTP stack. Markers gate
PR-safe (``performance_fast``) vs extended load (``performance_extended``).
"""

from __future__ import annotations

import statistics
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import pytest
from sqlalchemy.orm import Session

from ecommerce_backoffice_api.domain.entities import CustomerCredit, Product, Store, User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.infrastructure.persistence.models import UserModel
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyCreditRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStoreRepository,
    SqlAlchemyUserRepository,
)

pytest_plugins = ["tests.database.conftest"]

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class TimingResult:
    """Summary of warmup + measured samples for one timed operation."""

    samples_seconds: tuple[float, ...]
    median_seconds: float
    max_seconds: float


@dataclass(frozen=True, slots=True)
class PerfTenant:
    """Seeded tenant used by critical-path and persona projection benches."""

    owner: User
    customer: User
    delivery: User
    admin: User
    store: Store
    product: Product


def measure_operation(
    operation: Callable[[], T],
    *,
    iterations: int = 5,
    warmup: int = 1,
) -> tuple[T, TimingResult]:
    """Run ``operation`` with warmup, then return the last result and timings."""
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    last: T
    for _ in range(warmup):
        last = operation()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        last = operation()
        samples.append(time.perf_counter() - started)
    return last, TimingResult(
        samples_seconds=tuple(samples),
        median_seconds=statistics.median(samples),
        max_seconds=max(samples),
    )


def assert_under_slo(
    operation: Callable[[], T],
    *,
    label: str,
    max_median_seconds: float,
    iterations: int = 5,
    warmup: int = 1,
) -> tuple[T, TimingResult]:
    """Assert the median latency of ``operation`` stays under an SLO budget."""
    result, timing = measure_operation(operation, iterations=iterations, warmup=warmup)
    assert timing.median_seconds <= max_median_seconds, (
        f"{label} median {timing.median_seconds:.4f}s exceeded SLO "
        f"{max_median_seconds:.4f}s (samples={timing.samples_seconds!r})"
    )
    return result, timing


def seed_perf_tenant(session: Session, *, order_ready_stock: int = 50) -> PerfTenant:
    """Create one store with admin/owner/customer/delivery principals and stock."""
    users = SqlAlchemyUserRepository(session)
    stores = SqlAlchemyStoreRepository(session)
    products = SqlAlchemyProductRepository(session)
    credits = SqlAlchemyCreditRepository(session)

    admin = users.add(
        User(
            email=f"admin-{uuid.uuid4().hex[:8]}@perf.test",
            password_hash="unused",
            role=UserRole.ADMIN,
            full_name="Perf Admin",
        )
    )
    owner = users.add(
        User(
            email=f"owner-{uuid.uuid4().hex[:8]}@perf.test",
            password_hash="unused",
            role=UserRole.STORE_OWNER,
            full_name="Perf Owner",
        )
    )
    store = stores.add(
        Store(
            name="Perf Store",
            owner_user_id=owner.id or 0,
            public_id=str(uuid.uuid4()),
        )
    )
    assert owner.id is not None and store.id is not None
    owner_model = session.get(UserModel, owner.id)
    assert owner_model is not None
    owner_model.store_id = store.id
    owner.store_id = store.id

    customer = users.add(
        User(
            email=f"customer-{uuid.uuid4().hex[:8]}@perf.test",
            password_hash="unused",
            role=UserRole.CUSTOMER,
            full_name="Perf Customer",
            store_id=store.id,
        )
    )
    assert customer.id is not None
    credits.save(CustomerCredit(user_id=customer.id, balance_cents=5_000_000))

    delivery = users.add(
        User(
            email=f"delivery-{uuid.uuid4().hex[:8]}@perf.test",
            password_hash="unused",
            role=UserRole.DELIVERY_MANAGER,
            full_name="Perf Delivery",
            store_id=None,
        )
    )
    product = products.add(
        Product(
            store_id=store.id,
            name="Perf Widget",
            description="perf",
            price_cents=1000,
            stock_quantity=order_ready_stock,
        )
    )
    return PerfTenant(
        owner=owner,
        customer=customer,
        delivery=delivery,
        admin=admin,
        store=store,
        product=product,
    )


@pytest.fixture()
def perf_tenant(db_session: Session) -> PerfTenant:
    return seed_perf_tenant(db_session)
