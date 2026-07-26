"""Pydantic schemas for store theme endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StoreThemeResponse(BaseModel):
    """Metadata for a persisted store theme artifact."""

    id: int
    store_id: int
    content_type: str
    artifact_size_bytes: int = Field(ge=0)
