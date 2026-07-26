"""Pydantic schemas for admin directory and audit-trail endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_backoffice_api.domain.enums import AuditOutcome, UserRole


class AdminUserResponse(BaseModel):
    """Directory projection of a backoffice principal."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    full_name: str
    store_id: int | None


class AuditEventResponse(BaseModel):
    """Serialized admin audit-trail event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int
    action: str
    resource_type: str
    resource_id: str | None
    outcome: AuditOutcome
    detail: str
    created_at: datetime


class AuditEventListResponse(BaseModel):
    """Envelope for recent audit events."""

    events: list[AuditEventResponse] = Field(default_factory=list)
