"""Admin audit-trail recording (iter-02 A09 — remediated).

Secure behaviour:
- Authorization failures are persisted and logged as domain audit events.
- Application logs are structured JSON with a redaction filter — bearer tokens
  and PII never appear in log messages.
- Repeated authorization denials trigger a threshold alert log line.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from ecommerce_backoffice_api.application.ports.repositories import AuditEventRepository
from ecommerce_backoffice_api.domain.entities import AuditEvent, User
from ecommerce_backoffice_api.domain.enums import AuditOutcome

_LOGGER = logging.getLogger("ecommerce_backoffice_api.audit")

# Alert when this many authorization denials are recorded in-process.
_AUTHORIZATION_DENIAL_ALERT_THRESHOLD = 5

_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+\S+")
_JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class RedactingFilter(logging.Filter):
    """Strip tokens and email-shaped strings from log records (defense in depth)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", message)
        redacted = _JWT_PATTERN.sub("[REDACTED_TOKEN]", redacted)
        redacted = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def _ensure_redacting_filter() -> None:
    if any(isinstance(existing, RedactingFilter) for existing in _LOGGER.filters):
        return
    _LOGGER.addFilter(RedactingFilter())


def _emit_structured(event_name: str, payload: dict[str, object]) -> None:
    _ensure_redacting_filter()
    body = {"event": event_name, **payload}
    _LOGGER.info("%s", json.dumps(body, sort_keys=True, default=str))


class AdminAuditTrail:
    """Persist and log admin security events without leaking secrets or PII."""

    def __init__(self, audit_event_repository: AuditEventRepository) -> None:
        self._audit_event_repository = audit_event_repository
        self._authorization_denial_count = 0

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
        """Persist a successful admin action and emit a redacted structured log."""
        # Accepted for API compatibility with call sites; never logged.
        del access_token, subject_email, subject_full_name, shipping_address

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
        _emit_structured(
            "admin_action",
            {
                "action": action,
                "actor_user_id": actor.id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "outcome": AuditOutcome.SUCCESS.value,
                "detail": detail,
            },
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
        """Persist and log a denied authorization attempt; alert on threshold."""
        if actor.id is None:
            raise ValueError("Audit actor must have a persistent id.")
        event = AuditEvent(
            actor_user_id=actor.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=AuditOutcome.AUTHORIZATION_DENIED,
            detail=detail,
            created_at=datetime.now(UTC),
        )
        self._audit_event_repository.add(event)
        self._authorization_denial_count += 1
        _emit_structured(
            "admin_authorization_denied",
            {
                "action": action,
                "actor_user_id": actor.id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "outcome": AuditOutcome.AUTHORIZATION_DENIED.value,
                "detail": detail,
            },
        )
        if self._authorization_denial_count >= _AUTHORIZATION_DENIAL_ALERT_THRESHOLD:
            _ensure_redacting_filter()
            _LOGGER.warning(
                "%s",
                json.dumps(
                    {
                        "event": "authorization_denial_threshold_exceeded",
                        "count": self._authorization_denial_count,
                        "threshold": _AUTHORIZATION_DENIAL_ALERT_THRESHOLD,
                    },
                    sort_keys=True,
                ),
            )
