"""Store theme upload use cases (iter-03 A08 vehicle).

VULNERABLE (red phase): uploaded theme artifacts are accepted without HMAC or
checksum verification. An optional ``signature_hex`` is accepted for API
compatibility but never validated.

Remediation plan (not implemented here): require an HMAC-SHA256 signature over
the artifact bytes, reject missing/invalid signatures, and optionally verify a
checksum manifest before persistence.
"""

from __future__ import annotations

from ecommerce_backoffice_api.application.ports.repositories import StoreRepository, ThemeRepository
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import StoreTheme, User
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, NotFoundError


class UploadStoreTheme:
    """Persist a storefront theme artifact for a tenant store."""

    def __init__(
        self,
        theme_repository: ThemeRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._theme_repository = theme_repository
        self._store_repository = store_repository

    def execute(
        self,
        *,
        actor: User,
        store_id: int,
        artifact_bytes: bytes,
        content_type: str = "application/octet-stream",
        signature_hex: str | None = None,
    ) -> StoreTheme:
        if not authorization.can_write_store_theme(actor, store_id):
            raise AuthorizationError("Not permitted to upload a theme for this store.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")
        # Deliberately trusts client-supplied bytes. ``signature_hex`` is ignored
        # so unsigned and forged artifacts are accepted (A08 integrity failure).
        _ = signature_hex
        return self._theme_repository.save(
            StoreTheme(
                store_id=store_id,
                artifact_bytes=artifact_bytes,
                content_type=content_type.strip() or "application/octet-stream",
            )
        )


class GetStoreTheme:
    """Fetch the theme artifact for a store when the actor may read the store."""

    def __init__(
        self,
        theme_repository: ThemeRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._theme_repository = theme_repository
        self._store_repository = store_repository

    def execute(self, *, actor: User, store_id: int) -> StoreTheme:
        if not authorization.can_read_store(actor, store_id):
            raise AuthorizationError("Not permitted to read this store theme.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")
        theme = self._theme_repository.get_for_store(store_id)
        if theme is None:
            raise NotFoundError(f"Theme for store {store_id} was not found.")
        return theme
