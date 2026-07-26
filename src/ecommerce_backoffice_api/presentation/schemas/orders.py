"""Pydantic schemas for order endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_backoffice_api.domain.enums import OrderStatus


class OrderLineResponse(BaseModel):
    """Order line representation."""

    id: int
    product_id: int
    quantity: int
    unit_price_cents: int


class OrderResponse(BaseModel):
    """Full order representation including customer personally identifiable fields."""

    id: int
    store_id: int
    customer_user_id: int
    status: OrderStatus
    customer_email: str
    customer_full_name: str
    shipping_address: str
    lines: list[OrderLineResponse]
    notes: str = ""


class AnonymizedOrderResponse(BaseModel):
    """Delivery-manager order representation without customer PII."""

    id: int
    store_id: int
    status: OrderStatus
    lines: list[OrderLineResponse]
    notes: str = ""


class OrderStatusUpdateRequest(BaseModel):
    """Payload for patching an order status."""

    status: OrderStatus = Field(...)


class OrderNotesUpdateRequest(BaseModel):
    """Payload for patching free-text order notes.

    VULNERABLE (A05): ``notes`` accepts arbitrary markup with no length/charset
    constraints; the web UI renders it with Jinja2 ``|safe``.

    PLAN FIX (A05): Field(max_length=...), reject HTML/script patterns or strip
    tags; encode on output; add CSP.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    notes: str
