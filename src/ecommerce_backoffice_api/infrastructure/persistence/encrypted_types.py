"""SQLAlchemy types that encrypt sensitive string fields at rest (Fernet)."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text, TypeDecorator


def _resolve_fernet() -> Fernet:
    """Return a Fernet instance from ``PII_ENCRYPTION_KEY`` or a demo-derived key."""
    configured = os.environ.get("PII_ENCRYPTION_KEY", "").strip()
    if configured:
        key = configured.encode("utf-8")
    else:
        # Deterministic demo fallback so local/CI can boot without extra secrets.
        # Production must set ``PII_ENCRYPTION_KEY`` via secret management.
        digest = hashlib.sha256(b"phase1b-demo-only-pii-encryption-key").digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


class EncryptedText(TypeDecorator[str]):
    """Persist UTF-8 strings as Fernet ciphertext; decrypt transparently on load."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: object) -> str:
        if value is None or value == "":
            return ""
        token = _resolve_fernet().encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def process_result_value(self, value: str | None, dialect: object) -> str:
        if value is None or value == "":
            return ""
        try:
            return _resolve_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Legacy plaintext rows (pre-remediation) remain readable once.
            return value
