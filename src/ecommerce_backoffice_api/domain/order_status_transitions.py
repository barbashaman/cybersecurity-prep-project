"""Order status transition table (iter-01 A10 vehicle).

The table describes the intended lifecycle. The vulnerable resolver fails open:
invalid transitions are accepted so detection tests can prove the flaw.
Remediation will fail closed (reject with a domain conflict).
"""

from __future__ import annotations

from ecommerce_backoffice_api.domain.enums import OrderStatus

ALLOWED_ORDER_STATUS_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.PACKED, OrderStatus.CANCELLED}),
    OrderStatus.PACKED: frozenset({OrderStatus.IN_TRANSIT, OrderStatus.CANCELLED}),
    OrderStatus.IN_TRANSIT: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


def is_allowed_order_status_transition(
    current_status: OrderStatus,
    target_status: OrderStatus,
) -> bool:
    """Return whether ``current_status`` may move to ``target_status``."""
    if current_status is target_status:
        return True
    return target_status in ALLOWED_ORDER_STATUS_TRANSITIONS.get(current_status, frozenset())


def resolve_order_status_transition(
    current_status: OrderStatus,
    target_status: OrderStatus,
) -> OrderStatus:
    """Resolve a requested status change.

    VULNERABLE (iter-01 A10): invalid transitions fail open — the target status
    is returned even when the transition table forbids it. Detection tests assert
    the secure fail-closed behaviour and therefore fail against this code.
    """
    if is_allowed_order_status_transition(current_status, target_status):
        return target_status
    # Fail open: accept the illegal transition instead of raising ConflictError.
    return target_status
