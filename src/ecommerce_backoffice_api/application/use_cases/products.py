"""Product catalog use cases."""

from __future__ import annotations

import csv
import io

from ecommerce_backoffice_api.application.ports.repositories import (
    ProductRepository,
    StoreRepository,
)
from ecommerce_backoffice_api.application.use_cases.audit import AdminAuditTrail
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import Product, User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, NotFoundError


class ListProductsForStore:
    """List products for a store the actor may read."""

    def __init__(
        self,
        product_repository: ProductRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._product_repository = product_repository
        self._store_repository = store_repository

    def execute(self, *, actor: User, store_id: int) -> list[Product]:
        if not authorization.can_read_store_catalog(actor, store_id):
            raise AuthorizationError("Not permitted to read this store catalog.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")
        return self._product_repository.list_for_store(store_id)


class CreateProduct:
    """Create a product in a store the actor may write."""

    def __init__(
        self,
        product_repository: ProductRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._product_repository = product_repository
        self._store_repository = store_repository

    def execute(
        self,
        *,
        actor: User,
        store_id: int,
        name: str,
        description: str,
        price_cents: int,
        is_active: bool = True,
        stock_quantity: int = 0,
    ) -> Product:
        if not authorization.can_write_store_catalog(actor, store_id):
            raise AuthorizationError("Not permitted to write this store catalog.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")
        product = Product(
            store_id=store_id,
            name=name.strip(),
            description=description.strip(),
            price_cents=price_cents,
            is_active=is_active,
            stock_quantity=stock_quantity,
        )
        return self._product_repository.add(product)


class GetProduct:
    """Fetch a product if the actor may read its store catalog."""

    def __init__(self, product_repository: ProductRepository) -> None:
        self._product_repository = product_repository

    def execute(self, *, actor: User, product_id: int) -> Product:
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} was not found.")
        if not authorization.can_read_store_catalog(actor, product.store_id):
            raise AuthorizationError("Not permitted to read this product.")
        return product


class UpdateProduct:
    """Patch product fields when the actor may write the catalog."""

    def __init__(
        self,
        product_repository: ProductRepository,
        admin_audit_trail: AdminAuditTrail,
    ) -> None:
        self._product_repository = product_repository
        self._admin_audit_trail = admin_audit_trail

    def execute(
        self,
        *,
        actor: User,
        product_id: int,
        name: str | None = None,
        description: str | None = None,
        price_cents: int | None = None,
        is_active: bool | None = None,
        stock_quantity: int | None = None,
        access_token: str | None = None,
    ) -> Product:
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} was not found.")
        if not authorization.can_write_store_catalog(actor, product.store_id):
            self._admin_audit_trail.record_authorization_failure(
                actor=actor,
                action="product.update",
                resource_type="product",
                resource_id=str(product_id),
                detail="Not permitted to write this product.",
            )
            raise AuthorizationError("Not permitted to write this product.")
        if name is not None:
            product.name = name.strip()
        if description is not None:
            product.description = description.strip()
        if price_cents is not None:
            product.price_cents = price_cents
        if is_active is not None:
            product.is_active = is_active
        if stock_quantity is not None:
            product.stock_quantity = stock_quantity
        saved = self._product_repository.save(product)
        if actor.role is UserRole.ADMIN:
            self._admin_audit_trail.record_success(
                actor=actor,
                action="product.update",
                resource_type="product",
                resource_id=str(product_id),
                detail=f"Updated product {product_id}.",
                access_token=access_token,
            )
        return saved


class ImportProductsFromCsv:
    """Bulk-create products from a CSV payload for a store catalog.

    Expected columns: ``name``, ``description``, ``price_cents``, ``is_active``,
    ``quantity_hint``.

    Malformed rows may still raise ``KeyError`` / ``ZeroDivisionError``; the
    presentation layer's RFC 9457 handler must never echo those stack frames.
    """

    def __init__(
        self,
        product_repository: ProductRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._product_repository = product_repository
        self._store_repository = store_repository

    def execute(self, *, actor: User, store_id: int, csv_text: str) -> list[Product]:
        if not authorization.can_write_store_catalog(actor, store_id):
            raise AuthorizationError("Not permitted to write this store catalog.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")

        reader = csv.DictReader(io.StringIO(csv_text))
        created: list[Product] = []
        for row in reader:
            # Deliberately brittle access — missing keys propagate as KeyError.
            name = row["name"].strip()
            description = row["description"].strip()
            price_cents = int(row["price_cents"])
            is_active = row["is_active"].strip().lower() in {"1", "true", "yes", "on"}
            quantity_hint = int(row["quantity_hint"])
            # Division by zero when quantity_hint is 0 — exceptional-condition vehicle.
            unit_share_cents = price_cents // quantity_hint

            product = Product(
                store_id=store_id,
                name=name,
                # Retain the computed share so the exceptional division is not DCE'd.
                description=f"{description} (unit_share_cents={unit_share_cents})",
                price_cents=price_cents,
                is_active=is_active,
            )
            created.append(self._product_repository.add(product))
        return created
