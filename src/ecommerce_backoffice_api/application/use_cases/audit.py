"""Admin audit-trail recording (iter-02 A09 vehicle — deliberately vulnerable).

VULNERABLE red-phase behaviour:
- Authorization failures are intentionally *not* persisted or logged.
- Successful admin actions emit plaintext application logs that include bearer
  tokens and PII (emails, names, shipping addresses).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ecommerce_backoffice_api.application.ports.repositories import AuditEventRepository
from ecommerce_backoffice_api.domain.entities import AuditEvent, User
from ecommerce_backoffice_api.domain.enums import AuditOutcome

_LOGGER = logging.getLogger("ecommerce_backoffice_api.audit")


class AdminAuditTrail:
    """Persist and log admin security events (with intentional A09 flaws)."""

    def __init__(self, audit_event_repository: AuditEventRepository) -> None:
        self._audit_event_repository = audit_event_repository

    def record_success(
        self,
        *,
        actor: User,
        action: str,
        resource_type: str,
        resource_id: str | None,
        detail: str,
        access_token: str | None = None,
        subject_email: str | None = None,
        subject_full_name: str | None = None,
        shipping_address: str | None = None,
    ) -> AuditEvent:
        """Persist a successful admin action and log it with plaintext secrets/PII."""
        if actor.id is None:
            raise ValueError("Audit actor must have a persistent id.")
        event = AuditEvent(
            actor_user_id=actor.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=AuditOutcome.SUCCESS,
            detail=detail,
            created_at=datetime.now(UTC),
        )
        saved = self._audit_event_repository.add(event)
        # VULNERABLE (A09): tokens and PII appear in plaintext application logs.
        _LOGGER.info(
            "admin_action action=%s actor_email=%s actor_full_name=%s "
            "subject_email=%s subject_full_name=%s shipping_address=%s "
            "authorization=Bearer %s detail=%s",
            action,
            actor.email,
            actor.full_name,
            subject_email or "",
            subject_full_name or "",
            shipping_address or "",
            access_token or "",
            detail,
        )
        return saved

    def record_authorization_failure(
        self,
        *,
        actor: User,
        action: str,
        resource_type: str,
        resource_id: str | None,
        detail: str,
    ) -> None:
        """Record a denied authorization attempt.

        VULNERABLE (A09): intentionally a no-op — authorization failures are not
        written to the audit trail and are not emitted to application logs.
        """
        del actor, action, resource_type, resource_id, detail
