"""Admin directory and audit-trail routes under ``/api/v1/admin``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ecommerce_backoffice_api.application.use_cases.admin import ListAuditEvents, ListUsers
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import DomainError, NotFoundError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_current_user,
    get_list_audit_events,
    get_list_users,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.admin import (
    AdminUserResponse,
    AuditEventListResponse,
    AuditEventResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListUsers, Depends(get_list_users)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> list[AdminUserResponse]:
    try:
        users = use_case.execute(actor=actor, access_token=_access_token(credentials))
    except DomainError as error:
        raise http_error_from_domain(error) from error
    responses: list[AdminUserResponse] = []
    for user in users:
        if user.id is None:
            raise http_error_from_domain(NotFoundError("User is missing a persistent identifier."))
        responses.append(
            AdminUserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                full_name=user.full_name,
                store_id=user.store_id,
            )
        )
    return responses


@router.get("/audit-events", response_model=AuditEventListResponse)
def list_audit_events(
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListAuditEvents, Depends(get_list_audit_events)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AuditEventListResponse:
    try:
        events = use_case.execute(
            actor=actor,
            limit=limit,
            access_token=_access_token(credentials),
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    serialized: list[AuditEventResponse] = []
    for event in events:
        if event.id is None:
            raise http_error_from_domain(
                NotFoundError("Audit event is missing a persistent identifier.")
            )
        serialized.append(
            AuditEventResponse(
                id=event.id,
                actor_user_id=event.actor_user_id,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                outcome=event.outcome,
                detail=event.detail,
                created_at=event.created_at,
            )
        )
    return AuditEventListResponse(events=serialized)
