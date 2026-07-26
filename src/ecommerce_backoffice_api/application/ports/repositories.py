"""Persistence ports for domain aggregates."""

from __future__ import annotations

from typing import Protocol

from ecommerce_backoffice_api.domain.entities import (
    AuditEvent,
    Coupon,
    CouponRedemption,
    CustomerCredit,
    Order,
    OrderReceipt,
    PasswordResetToken,
    Product,
    Store,
    StoreTheme,
    User,
)
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

    def update_password(self, user_id: int, password_hash: str) -> User:
        """Replace the password hash for ``user_id`` and return the user."""
        ...


class PasswordResetTokenRepository(Protocol):
    """Read/write access to password-reset tokens."""

    def save(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        """Persist a reset token and return it with an assigned id."""
        ...

    def get_by_token(self, token: str) -> PasswordResetToken | None:
        """Return the reset token row for ``token``, or None."""
        ...

    def delete_for_user(self, user_id: int) -> None:
        """Remove all reset tokens belonging to ``user_id``."""
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

    def search_for_store(self, store_id: int, query: str) -> list[Product]:
        """Return products in ``store_id`` whose name matches ``query``."""
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

    def update_notes(self, order_id: int, notes: str) -> Order:
        """Replace free-text notes on an existing order and return it."""
        ...


class ThemeRepository(Protocol):
    """Read/write access to store theme artifacts."""

    def get_for_store(self, store_id: int) -> StoreTheme | None:
        """Return the theme for ``store_id``, or None."""
        ...

    def save(self, theme: StoreTheme) -> StoreTheme:
        """Upsert the theme for a store and return it with an assigned id."""
        ...


class ReceiptRepository(Protocol):
    """Read/write access to order receipt blobs."""

    def get_for_order(self, order_id: int) -> OrderReceipt | None:
        """Return the receipt for ``order_id``, or None."""
        ...

    def save(self, receipt: OrderReceipt) -> OrderReceipt:
        """Upsert the receipt for an order and return it with an assigned id."""
        ...


class CreditRepository(Protocol):
    """Read/write access to mock customer credit balances."""

    def get_for_user(self, user_id: int) -> CustomerCredit | None:
        """Return the credit row for ``user_id``, or None."""
        ...

    def save(self, credit: CustomerCredit) -> CustomerCredit:
        """Upsert a credit balance and return it with an assigned id."""
        ...


class CouponRepository(Protocol):
    """Read/write access to discount coupons and redemptions."""

    def add(self, coupon: Coupon) -> Coupon:
        """Persist a new coupon and return it with an assigned id."""
        ...

    def get_by_code(self, store_id: int, code: str) -> Coupon | None:
        """Return the coupon for ``store_id`` + ``code``, or None."""
        ...

    def record_redemption(self, redemption: CouponRedemption) -> CouponRedemption:
        """Persist a coupon redemption ledger entry."""
        ...

    def has_been_redeemed(self, coupon_id: int) -> bool:
        """Return True when ``coupon_id`` already has a redemption row."""
        ...
