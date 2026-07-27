"""Store theme upload use cases (iter-03 A08 — remediated).

Theme artifacts require an HMAC-SHA256 hex signature over the raw bytes before
persistence. Missing or invalid signatures fail closed with ``ConflictError``.
"""

from __future__ import annotations

import hashlib
import hmac

from ecommerce_backoffice_api.application.ports.repositories import StoreRepository, ThemeRepository
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import StoreTheme, User
from ecommerce_backoffice_api.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
)

# Demo-only default used when the composition root does not inject a secret.
_DEFAULT_THEME_HMAC_SECRET = "phase1b-demo-only-theme-hmac-secret-change-me"  # noqa: S105  # nosec B105


def compute_theme_artifact_signature(*, artifact_bytes: bytes, secret: str) -> str:
    """Return the lowercase hex HMAC-SHA256 of ``artifact_bytes``."""
    digest = hmac.new(secret.encode("utf-8"), artifact_bytes, hashlib.sha256).hexdigest()
    return digest


def verify_theme_artifact_signature(
    *,
    artifact_bytes: bytes,
    signature_hex: str | None,
    secret: str,
) -> None:
    """Require a valid HMAC-SHA256 hex signature; raise ``ConflictError`` otherwise."""
    if signature_hex is None or not signature_hex.strip():
        raise ConflictError("Theme artifact signature is required.")
    expected = compute_theme_artifact_signature(artifact_bytes=artifact_bytes, secret=secret)
    candidate = signature_hex.strip().lower()
    if not hmac.compare_digest(expected, candidate):
        raise ConflictError("Theme artifact signature is invalid.")


class UploadStoreTheme:
    """Persist a storefront theme artifact for a tenant store."""

    def __init__(
        self,
        theme_repository: ThemeRepository,
        store_repository: StoreRepository,
        hmac_secret: str = _DEFAULT_THEME_HMAC_SECRET,
    ) -> None:
        self._theme_repository = theme_repository
        self._store_repository = store_repository
        self._hmac_secret = hmac_secret

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
        verify_theme_artifact_signature(
            artifact_bytes=artifact_bytes,
            signature_hex=signature_hex,
            secret=self._hmac_secret,
        )
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
