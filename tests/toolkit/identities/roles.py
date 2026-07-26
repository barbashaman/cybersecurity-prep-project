"""Security-relevant role constants.

Modelled as a typed enum rather than magic strings so that the role matrix the
access-control iterations (iter-04, iter-05, iter-10) depend on is
type-checked, not stringly-typed.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """The four tenancy roles in the backoffice domain."""

    ADMIN = "admin"
    STORE_OWNER = "store_owner"
    CUSTOMER = "customer"
    DELIVERY_MANAGER = "delivery_manager"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
