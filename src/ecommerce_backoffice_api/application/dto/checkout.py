"""Checkout / credits projections for iter-05 (A06)."""

from __future__ import annotations

from dataclasses import dataclass

from ecommerce_backoffice_api.application.dto.orders import OrderDetailView


@dataclass(frozen=True, slots=True)
class CreditBalanceView:
    """Customer mock-credit balance."""

    user_id: int
    balance_cents: int


@dataclass(frozen=True, slots=True)
class CouponView:
    """Store-scoped coupon projection."""

    id: int
    store_id: int
    code: str
    discount_percent: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class CheckoutResultView:
    """Result of placing an order with optional coupon discount."""

    order: OrderDetailView
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    coupon_code: str | None
    credits_charged_cents: int
