"""Pydantic schemas for order endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

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


class AnonymizedOrderResponse(BaseModel):
    """Delivery-manager order representation without customer PII."""

    id: int
    store_id: int
    status: OrderStatus
    lines: list[OrderLineResponse]


class OrderStatusUpdateRequest(BaseModel):
    """Payload for patching an order status."""

    status: OrderStatus = Field(...)
