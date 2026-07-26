"""Persistence ports for domain aggregates."""

from __future__ import annotations

from typing import Protocol

from ecommerce_backoffice_api.domain.entities import AuditEvent, Order, Product, Store, User
from ecommerce_backoffice_api.domain.enums import OrderStatus


class UserRepository(Protocol):
    """Read/write access to user aggregates."""

    def get_by_id(self, user_id: int) -> User | None:
        """Return the user with ``user_id``, or None."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Return the user with ``email``, or None."""
        ...

    def list_all(self) -> list[User]:
        """Return every persisted user (admin directory use cases)."""
        ...

    def add(self, user: User) -> User:
        """Persist a new user and return it with an assigned id."""
        ...


class AuditEventRepository(Protocol):
    """Read/write access to admin audit-trail events."""

    def add(self, event: AuditEvent) -> AuditEvent:
        """Persist a new audit event and return it with an assigned id."""
        ...

    def list_recent(self, *, limit: int = 100) -> list[AuditEvent]:
        """Return the most recent audit events, newest first."""
        ...


class StoreRepository(Protocol):
    """Read/write access to store aggregates."""

    def list_all(self) -> list[Store]:
        """Return every store."""
        ...

    def get_by_id(self, store_id: int) -> Store | None:
        """Return the store with ``store_id``, or None."""
        ...

    def add(self, store: Store) -> Store:
        """Persist a new store and return it with an assigned id."""
        ...


class ProductRepository(Protocol):
    """Read/write access to product aggregates."""

    def list_for_store(self, store_id: int) -> list[Product]:
        """Return products belonging to ``store_id``."""
        ...

    def get_by_id(self, product_id: int) -> Product | None:
        """Return the product with ``product_id``, or None."""
        ...

    def add(self, product: Product) -> Product:
        """Persist a new product and return it with an assigned id."""
        ...

    def save(self, product: Product) -> Product:
        """Persist updates to an existing product."""
        ...


class OrderRepository(Protocol):
    """Read/write access to order aggregates."""

    def list_for_store(self, store_id: int) -> list[Order]:
        """Return orders placed against ``store_id``."""
        ...

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        """Return a customer's orders within ``store_id``."""
        ...

    def get_by_id(self, order_id: int) -> Order | None:
        """Return the order with ``order_id``, or None."""
        ...

    def add(self, order: Order) -> Order:
        """Persist a new order and return it with an assigned id."""
        ...

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        """Update the status of an existing order and return it."""
        ...
