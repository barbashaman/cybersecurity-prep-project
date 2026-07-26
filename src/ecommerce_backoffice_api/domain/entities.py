"""Domain entities for the e-commerce backoffice baseline.

Integer primary keys are intentional for Phase 1b; predictable identifiers are
the vehicle for the IDOR work in a later iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ecommerce_backoffice_api.domain.enums import AuditOutcome, OrderStatus, UserRole


@dataclass(slots=True)
class User:
    """A backoffice principal with a single role and optional store tenancy."""

    email: str
    password_hash: str
    role: UserRole
    full_name: str
    store_id: int | None = None
    id: int | None = None


@dataclass(slots=True)
class Store:
    """A tenant store owned by one store-owner principal."""

    name: str
    owner_user_id: int | None = None
    id: int | None = None


@dataclass(slots=True)
class Product:
    """A catalog item belonging to exactly one store."""

    store_id: int
    name: str
    description: str
    price_cents: int
    is_active: bool = True
    stock_quantity: int = 0
    id: int | None = None


@dataclass(slots=True)
class OrderLine:
    """One line on an order: a product, quantity, and captured unit price."""

    product_id: int
    quantity: int
    unit_price_cents: int
    order_id: int | None = None
    id: int | None = None


@dataclass(slots=True)
class Order:
    """A customer order placed against a store.

    Customer contact fields are personally identifiable information and must not
    be exposed through delivery-manager facing ports.
    """

    store_id: int
    customer_user_id: int
    status: OrderStatus
    customer_email: str
    customer_full_name: str
    shipping_address: str
    lines: list[OrderLine] = field(default_factory=list)
    # VULNERABLE (A05): free-text notes are later rendered with Jinja2 ``|safe``.
    # PLAN FIX (A05): Pydantic validation + HTML output encoding (no ``|safe``) + CSP.
    notes: str = ""
    id: int | None = None


@dataclass(slots=True)
class AuditEvent:
    """A persisted admin audit-trail record for a security-relevant action."""

    actor_user_id: int
    action: str
    resource_type: str
    resource_id: str | None
    outcome: AuditOutcome
    detail: str
    created_at: datetime
    id: int | None = None


@dataclass(slots=True)
class StoreTheme:
    """A storefront theme artifact uploaded for a tenant store (iter-03 A08)."""

    store_id: int
    artifact_bytes: bytes
    content_type: str = "application/octet-stream"
    id: int | None = None


@dataclass(slots=True)
class OrderReceipt:
    """A purchase receipt blob persisted for an order (iter-03 A08)."""

    order_id: int
    payload_blob: bytes
    id: int | None = None


@dataclass(slots=True)
class PasswordResetToken:
    """A password-reset credential issued for a user (iter-04 A07)."""

    user_id: int
    token: str
    id: int | None = None


@dataclass(slots=True)
class CustomerCredit:
    """Mock customer credit balance used for demo checkout (iter-05 A06)."""

    user_id: int
    balance_cents: int
    id: int | None = None


@dataclass(slots=True)
class Coupon:
    """A store-scoped discount coupon (iter-05 A06)."""

    store_id: int
    code: str
    discount_percent: int
    is_active: bool = True
    id: int | None = None


@dataclass(slots=True)
class CouponRedemption:
    """A recorded coupon redemption (intended single-use ledger).

    PLAN FIX (A06): persist redemptions with a unique constraint on
    ``(coupon_id, user_id)`` (or global single-use on ``coupon_id``) so reuse
    is rejected at the database boundary.
    """

    coupon_id: int
    user_id: int
    order_id: int
    id: int | None = None
