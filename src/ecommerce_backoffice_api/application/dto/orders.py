"""Order projections exposed by application use cases.

The anonymised view deliberately omits personally identifiable fields so a
delivery-manager port cannot leak customer PII by construction (Interface
Segregation).
"""

from __future__ import annotations

from dataclasses import dataclass

from ecommerce_backoffice_api.domain.enums import OrderStatus


@dataclass(frozen=True, slots=True)
class OrderLineView:
    """A non-sensitive order line projection."""

    id: int
    product_id: int
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True, slots=True)
class OrderDetailView:
    """Full order view including customer personally identifiable information."""

    id: int
    store_id: int
    customer_user_id: int
    status: OrderStatus
    customer_email: str
    customer_full_name: str
    shipping_address: str
    lines: tuple[OrderLineView, ...]


@dataclass(frozen=True, slots=True)
class AnonymizedOrderView:
    """Delivery-manager order view with no customer personally identifiable data."""

    id: int
    store_id: int
    status: OrderStatus
    lines: tuple[OrderLineView, ...]
