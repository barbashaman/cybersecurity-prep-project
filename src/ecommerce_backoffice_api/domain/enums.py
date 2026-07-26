"""Domain enumerations for roles and order lifecycle states.

Security-relevant constants are typed here so outer layers never invent magic
strings for tenancy or workflow status.
"""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    """Tenancy roles recognised by the backoffice domain."""

    ADMIN = "admin"
    STORE_OWNER = "store_owner"
    CUSTOMER = "customer"
    DELIVERY_MANAGER = "delivery_manager"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class OrderStatus(str, Enum):
    """Lifecycle states for a customer order."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PACKED = "packed"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class AuditOutcome(str, Enum):
    """Outcome recorded on an admin audit-trail event."""

    SUCCESS = "success"
    AUTHORIZATION_DENIED = "authorization_denied"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
