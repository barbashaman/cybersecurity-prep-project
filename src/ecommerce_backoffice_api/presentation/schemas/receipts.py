"""Pydantic schemas for order receipt endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OrderReceiptStoreRequest(BaseModel):
    """Payload for storing a purchase receipt."""

    payload: dict[str, Any] = Field(default_factory=dict)


class OrderReceiptResponse(BaseModel):
    """Deserialized purchase receipt representation."""

    order_id: int
    payload: dict[str, Any]
