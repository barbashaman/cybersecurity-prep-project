"""Pydantic schemas for store endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StoreCreateRequest(BaseModel):
    """Payload for creating a store."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    owner_user_id: int | None = None


class StoreResponse(BaseModel):
    """Store resource representation."""

    id: int
    name: str
    owner_user_id: int | None
