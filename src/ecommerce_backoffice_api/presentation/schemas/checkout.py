"""Pydantic schemas for credits, coupons, and checkout (iter-05)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_backoffice_api.presentation.schemas.orders import OrderResponse


class CreditGrantRequest(BaseModel):
    """Payload for granting mock purchase credits."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int = Field(ge=1)
    amount_cents: int = Field(ge=1)


class CreditBalanceResponse(BaseModel):
    """Customer credit balance representation."""

    user_id: int
    balance_cents: int


class CouponCreateRequest(BaseModel):
    """Payload for creating a store coupon."""

    model_config = ConfigDict(str_strip_whitespace=True)

    store_id: int = Field(ge=1)
    code: str = Field(min_length=1, max_length=64)
    discount_percent: int = Field(ge=1, le=100)


class CouponResponse(BaseModel):
    """Coupon resource representation."""

    id: int
    store_id: int
    code: str
    discount_percent: int
    is_active: bool


class CheckoutLineRequest(BaseModel):
    """One checkout line.

    VULNERABLE (A06): ``quantity`` has no lower bound — negatives are accepted.
    PLAN FIX: Field(ge=1).
    """

    product_id: int = Field(ge=1)
    quantity: int


class CheckoutRequest(BaseModel):
    """Payload for placing an order with optional coupon."""

    model_config = ConfigDict(str_strip_whitespace=True)

    lines: list[CheckoutLineRequest] = Field(min_length=1)
    shipping_address: str = Field(min_length=1)
    coupon_code: str | None = None
    # PLAN FIX (A06): require and honour idempotency_key for safe retries.
    idempotency_key: str | None = None


class ApplyCouponRequest(BaseModel):
    """Payload for applying a coupon to an existing order."""

    model_config = ConfigDict(str_strip_whitespace=True)

    coupon_code: str = Field(min_length=1, max_length=64)


class CheckoutResponse(BaseModel):
    """Checkout result including discount and credit charge."""

    order: OrderResponse
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    coupon_code: str | None
    credits_charged_cents: int
