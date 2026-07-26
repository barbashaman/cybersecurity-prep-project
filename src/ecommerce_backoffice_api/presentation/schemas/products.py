"""Pydantic schemas for product endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProductCreateRequest(BaseModel):
    """Payload for creating a product."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    price_cents: int = Field(ge=0)
    is_active: bool = True
    stock_quantity: int = 0


class ProductUpdateRequest(BaseModel):
    """Partial update payload for a product."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    stock_quantity: int | None = None


class ProductResponse(BaseModel):
    """Product resource representation."""

    id: int
    store_id: int
    name: str
    description: str
    price_cents: int
    is_active: bool
    stock_quantity: int = 0


class ProductImportResponse(BaseModel):
    """Result envelope for a CSV bulk product import."""

    imported_count: int
    products: list[ProductResponse]
