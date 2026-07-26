"""Smoke tests for the order-status transition table (allowed paths only).

Fail-closed enforcement is asserted by ``tests/security/`` detection tests so
the quality-gate domain suite stays green during the vulnerable red phase.
"""

from __future__ import annotations

import pytest

from ecommerce_backoffice_api.domain.enums import OrderStatus
from ecommerce_backoffice_api.domain.order_status_transitions import (
    is_allowed_order_status_transition,
    resolve_order_status_transition,
)

pytestmark = pytest.mark.smoke


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (OrderStatus.PENDING, OrderStatus.CONFIRMED),
        (OrderStatus.CONFIRMED, OrderStatus.PACKED),
        (OrderStatus.PACKED, OrderStatus.IN_TRANSIT),
        (OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED),
        (OrderStatus.PENDING, OrderStatus.CANCELLED),
        (OrderStatus.DELIVERED, OrderStatus.DELIVERED),
    ],
)
def test_allowed_order_status_transitions(
    current_status: OrderStatus,
    target_status: OrderStatus,
) -> None:
    assert is_allowed_order_status_transition(current_status, target_status)
    assert resolve_order_status_transition(current_status, target_status) is target_status


def test_transition_table_marks_terminal_regressions_as_disallowed() -> None:
    assert not is_allowed_order_status_transition(OrderStatus.DELIVERED, OrderStatus.PENDING)
    assert not is_allowed_order_status_transition(OrderStatus.CANCELLED, OrderStatus.CONFIRMED)
