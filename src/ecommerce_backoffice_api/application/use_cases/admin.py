"""Admin directory and audit-trail query use cases (iter-02)."""

from __future__ import annotations

from ecommerce_backoffice_api.application.ports.repositories import (
    AuditEventRepository,
    UserRepository,
)
from ecommerce_backoffice_api.application.use_cases.audit import AdminAuditTrail
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import AuditEvent, User
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError


class ListUsers:
    """List all backoffice users (admin only) and record an audit event."""

    def __init__(
        self,
        user_repository: UserRepository,
        admin_audit_trail: AdminAuditTrail,
    ) -> None:
        self._user_repository = user_repository
        self._admin_audit_trail = admin_audit_trail

    def execute(self, *, actor: User, access_token: str | None = None) -> list[User]:
        if not authorization.can_list_users(actor):
            self._admin_audit_trail.record_authorization_failure(
                actor=actor,
                action="user.list",
                resource_type="user",
                resource_id=None,
                detail="Not permitted to list users.",
            )
            raise AuthorizationError("Not permitted to list users.")
        users = self._user_repository.list_all()
        self._admin_audit_trail.record_success(
            actor=actor,
            action="user.list",
            resource_type="user",
            resource_id=None,
            detail=f"Listed {len(users)} users.",
            access_token=access_token,
        )
        return users


class ListAuditEvents:
    """Return recent admin audit-trail events (admin only)."""

    def __init__(
        self,
        audit_event_repository: AuditEventRepository,
        admin_audit_trail: AdminAuditTrail,
    ) -> None:
        self._audit_event_repository = audit_event_repository
        self._admin_audit_trail = admin_audit_trail

    def execute(
        self,
        *,
        actor: User,
        limit: int = 100,
        access_token: str | None = None,
    ) -> list[AuditEvent]:
        if not authorization.can_list_audit_events(actor):
            self._admin_audit_trail.record_authorization_failure(
                actor=actor,
                action="audit.list",
                resource_type="audit_event",
                resource_id=None,
                detail="Not permitted to list audit events.",
            )
            raise AuthorizationError("Not permitted to list audit events.")
        events = self._audit_event_repository.list_recent(limit=limit)
        self._admin_audit_trail.record_success(
            actor=actor,
            action="audit.list",
            resource_type="audit_event",
            resource_id=None,
            detail=f"Listed {len(events)} audit events.",
            access_token=access_token,
        )
        return events
