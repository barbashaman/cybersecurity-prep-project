"""Order status transition table (iter-01 A10 vehicle).

The table describes the intended lifecycle. Remediated behaviour fails closed:
invalid transitions raise :class:`ConflictError`.
"""

from __future__ import annotations

from ecommerce_backoffice_api.domain.enums import OrderStatus
from ecommerce_backoffice_api.domain.exceptions import ConflictError

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
    """Resolve a requested status change, failing closed on illegal transitions."""
    if is_allowed_order_status_transition(current_status, target_status):
        return target_status
    raise ConflictError(
        f"Order status transition from {current_status.value} to {target_status.value} "
        "is not permitted."
    )
