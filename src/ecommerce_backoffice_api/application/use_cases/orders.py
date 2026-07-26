"""Order use cases with delivery-manager anonymization."""

from __future__ import annotations

from ecommerce_backoffice_api.application.dto.orders import (
    AnonymizedOrderView,
    OrderDetailView,
    OrderLineView,
)
from ecommerce_backoffice_api.application.ports.repositories import OrderRepository, StoreRepository
from ecommerce_backoffice_api.application.use_cases.audit import AdminAuditTrail
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import Order, User
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, NotFoundError
from ecommerce_backoffice_api.domain.order_status_transitions import resolve_order_status_transition


def _to_line_views(order: Order) -> tuple[OrderLineView, ...]:
    views: list[OrderLineView] = []
    for line in order.lines:
        if line.id is None:
            continue
        views.append(
            OrderLineView(
                id=line.id,
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
            )
        )
    return tuple(views)


def to_order_detail_view(order: Order) -> OrderDetailView:
    """Map a domain order to the full (PII-bearing) view."""
    if order.id is None:
        raise NotFoundError("Order is missing a persistent identifier.")
    return OrderDetailView(
        id=order.id,
        store_id=order.store_id,
        customer_user_id=order.customer_user_id,
        status=order.status,
        customer_email=order.customer_email,
        customer_full_name=order.customer_full_name,
        shipping_address=order.shipping_address,
        lines=_to_line_views(order),
    )


def to_anonymized_order_view(order: Order) -> AnonymizedOrderView:
    """Map a domain order to the delivery-manager PII-free view."""
    if order.id is None:
        raise NotFoundError("Order is missing a persistent identifier.")
    return AnonymizedOrderView(
        id=order.id,
        store_id=order.store_id,
        status=order.status,
        lines=_to_line_views(order),
    )


class ListOrdersForStore:
    """List orders for a store, filtered and projected per role."""

    def __init__(
        self,
        order_repository: OrderRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._order_repository = order_repository
        self._store_repository = store_repository

    def execute(
        self, *, actor: User, store_id: int
    ) -> list[OrderDetailView] | list[AnonymizedOrderView]:
        if not authorization.can_list_store_orders(actor, store_id):
            raise AuthorizationError("Not permitted to list orders for this store.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")

        if actor.role is UserRole.CUSTOMER and actor.id is not None:
            orders = self._order_repository.list_for_store_and_customer(store_id, actor.id)
        else:
            orders = self._order_repository.list_for_store(store_id)

        if authorization.must_anonymize_order_for(actor):
            return [to_anonymized_order_view(order) for order in orders]
        return [to_order_detail_view(order) for order in orders]


class GetOrder:
    """Fetch one order with role-appropriate projection."""

    def __init__(
        self,
        order_repository: OrderRepository,
        admin_audit_trail: AdminAuditTrail,
    ) -> None:
        self._order_repository = order_repository
        self._admin_audit_trail = admin_audit_trail

    def execute(
        self,
        *,
        actor: User,
        order_id: int,
        access_token: str | None = None,
    ) -> OrderDetailView | AnonymizedOrderView:
        order = self._order_repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        if not authorization.can_read_order(actor, order):
            self._admin_audit_trail.record_authorization_failure(
                actor=actor,
                action="order.read",
                resource_type="order",
                resource_id=str(order_id),
                detail="Not permitted to read this order.",
            )
            raise AuthorizationError("Not permitted to read this order.")
        if actor.role is UserRole.ADMIN:
            self._admin_audit_trail.record_success(
                actor=actor,
                action="order.read",
                resource_type="order",
                resource_id=str(order_id),
                detail=f"Read order {order_id}.",
                access_token=access_token,
            )
        if authorization.must_anonymize_order_for(actor):
            return to_anonymized_order_view(order)
        return to_order_detail_view(order)


class UpdateOrderStatus:
    """Transition an order's status when the actor is permitted."""

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(
        self, *, actor: User, order_id: int, status: OrderStatus
    ) -> OrderDetailView | AnonymizedOrderView:
        order = self._order_repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        if not authorization.can_update_order_status(actor, order):
            raise AuthorizationError("Not permitted to update this order status.")
        # Transition table is consulted, but the vulnerable resolver fails open.
        resolved_status = resolve_order_status_transition(order.status, status)
        updated = self._order_repository.update_status(order_id, resolved_status)
        if authorization.must_anonymize_order_for(actor):
            return to_anonymized_order_view(updated)
        return to_order_detail_view(updated)
