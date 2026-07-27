"""Revenue analytics use case with centralized access-control enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from ecommerce_backoffice_api.application.dto.revenue import StoreRevenueView
from ecommerce_backoffice_api.application.ports.repositories import OrderRepository, StoreRepository
from ecommerce_backoffice_api.domain.entities import Store, User
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, NotFoundError


@dataclass(frozen=True, slots=True)
class RevenueAccessPolicy:
    """Centralized policy for revenue endpoints."""

    def can_read_store_revenue(self, *, actor: User, store: Store) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        if actor.role is UserRole.STORE_OWNER:
            return actor.store_id == store.id
        return False


class GetStoreRevenue:
    """Return revenue analytics for exactly one authorized store."""

    def __init__(
        self,
        store_repository: StoreRepository,
        order_repository: OrderRepository,
        policy: RevenueAccessPolicy | None = None,
    ) -> None:
        self._store_repository = store_repository
        self._order_repository = order_repository
        self._policy = policy or RevenueAccessPolicy()

    def execute(self, *, actor: User, store_public_id: str) -> StoreRevenueView:
        store = self._store_repository.get_by_public_id(store_public_id.strip().lower())
        if store is None or store.id is None:
            raise NotFoundError("Store was not found.")
        if not self._policy.can_read_store_revenue(actor=actor, store=store):
            raise AuthorizationError("Not permitted to read this store revenue.")

        orders = self._order_repository.list_for_store(store.id)
        paid_orders = [order for order in orders if order.status is not OrderStatus.CANCELLED]
        gross_revenue_cents = sum(
            sum(line.quantity * line.unit_price_cents for line in order.lines)
            for order in paid_orders
        )
        return StoreRevenueView(
            store_public_id=store.public_id or "",
            store_name=store.name,
            total_orders=len(orders),
            paid_orders=len(paid_orders),
            gross_revenue_cents=gross_revenue_cents,
        )
