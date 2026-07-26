"""Pure authorization policies for store-scoped resources.

These functions are the single source of truth for "who may do what". Routers
and use cases call them; they contain no I/O and import only the domain.
"""

from __future__ import annotations

from ecommerce_backoffice_api.domain.entities import Order, User
from ecommerce_backoffice_api.domain.enums import UserRole


def can_list_all_stores(actor: User) -> bool:
    """Admins and delivery managers may enumerate every store."""
    return actor.role in {UserRole.ADMIN, UserRole.DELIVERY_MANAGER}


def can_read_store(actor: User, store_id: int) -> bool:
    """Return whether ``actor`` may view the named store."""
    if actor.role in {UserRole.ADMIN, UserRole.DELIVERY_MANAGER}:
        return True
    if actor.role in {UserRole.STORE_OWNER, UserRole.CUSTOMER}:
        return actor.store_id == store_id
    return False


def can_create_store(actor: User) -> bool:
    """Only admins may create stores in the baseline."""
    return actor.role is UserRole.ADMIN


def can_read_store_catalog(actor: User, store_id: int) -> bool:
    """Catalog visibility: admin, owning store staff/customer, delivery manager."""
    if actor.role in {UserRole.ADMIN, UserRole.DELIVERY_MANAGER}:
        return True
    if actor.role in {UserRole.STORE_OWNER, UserRole.CUSTOMER}:
        return actor.store_id == store_id
    return False


def can_write_store_catalog(actor: User, store_id: int) -> bool:
    """Product writes: admin or the owning store owner."""
    if actor.role is UserRole.ADMIN:
        return True
    if actor.role is UserRole.STORE_OWNER:
        return actor.store_id == store_id
    return False


def can_read_order(actor: User, order: Order) -> bool:
    """Order read access; delivery managers see an anonymised projection later."""
    if actor.role in {UserRole.ADMIN, UserRole.DELIVERY_MANAGER}:
        return True
    if actor.role is UserRole.STORE_OWNER:
        return actor.store_id == order.store_id
    if actor.role is UserRole.CUSTOMER:
        return actor.id == order.customer_user_id
    return False


def can_list_store_orders(actor: User, store_id: int) -> bool:
    """Who may list orders for a store (customers see only their own later)."""
    if actor.role in {UserRole.ADMIN, UserRole.DELIVERY_MANAGER}:
        return True
    if actor.role is UserRole.STORE_OWNER:
        return actor.store_id == store_id
    if actor.role is UserRole.CUSTOMER:
        return actor.store_id == store_id
    return False


def can_update_order_status(actor: User, order: Order) -> bool:
    """Status updates: admin, delivery manager, or owning store owner."""
    if actor.role in {UserRole.ADMIN, UserRole.DELIVERY_MANAGER}:
        return True
    if actor.role is UserRole.STORE_OWNER:
        return actor.store_id == order.store_id
    return False


def must_anonymize_order_for(actor: User) -> bool:
    """Delivery managers receive Interface-Segregated, PII-free order views."""
    return actor.role is UserRole.DELIVERY_MANAGER


def can_list_users(actor: User) -> bool:
    """Only admins may enumerate backoffice principals."""
    return actor.role is UserRole.ADMIN


def can_list_audit_events(actor: User) -> bool:
    """Only admins may read the admin audit trail."""
    return actor.role is UserRole.ADMIN


def can_write_store_theme(actor: User, store_id: int) -> bool:
    """Theme uploads: admin or the owning store owner."""
    return can_write_store_catalog(actor, store_id)


def can_manage_order_receipt(actor: User, order: Order) -> bool:
    """Receipt store/load: admin, owning store owner, or the ordering customer."""
    if actor.role is UserRole.ADMIN:
        return True
    if actor.role is UserRole.STORE_OWNER:
        return actor.store_id == order.store_id
    if actor.role is UserRole.CUSTOMER:
        return actor.id == order.customer_user_id
    return False


def can_update_order_notes(actor: User, order: Order) -> bool:
    """Order-notes updates: same principals as receipt management."""
    return can_manage_order_receipt(actor, order)


def can_grant_credits(actor: User) -> bool:
    """Mock credit grants: admin or the customer themselves (demo purchase)."""
    return actor.role in {UserRole.ADMIN, UserRole.CUSTOMER}


def can_manage_coupons(actor: User, store_id: int) -> bool:
    """Coupon create: admin or the owning store owner."""
    return can_write_store_catalog(actor, store_id)


def can_place_order(actor: User, store_id: int) -> bool:
    """Checkout: customers of the store (or admin acting for demos)."""
    if actor.role is UserRole.ADMIN:
        return True
    if actor.role is UserRole.CUSTOMER:
        return actor.store_id == store_id
    return False
