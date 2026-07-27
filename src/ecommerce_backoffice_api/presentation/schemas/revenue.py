"""Pydantic schemas for revenue analytics endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class StoreRevenueResponse(BaseModel):
    """Store-scoped revenue analytics projection."""

    store_public_id: str
    store_name: str
    total_orders: int
    paid_orders: int
    gross_revenue_cents: int
