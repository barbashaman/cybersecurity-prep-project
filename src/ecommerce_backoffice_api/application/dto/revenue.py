"""DTOs for cross-store revenue analytics (iter-10 A01)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoreRevenueView:
    store_public_id: str
    store_name: str
    total_orders: int
    paid_orders: int
    gross_revenue_cents: int
