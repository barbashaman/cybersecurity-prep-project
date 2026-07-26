"""Password hasher adapters implementing the application port.

Phase 1b shipped bcrypt. iter-07 (A04 red) intentionally wires MD5 so detection
can prove the weak KDF; remediation restores Argon2id (or strong bcrypt).
"""

from __future__ import annotations

import hashlib

import bcrypt

from ecommerce_backoffice_api.application.ports.security import PasswordHasher


class BcryptPasswordHasher:
    """Hash and verify passwords with bcrypt (kept for remediation / Phase 1b)."""

    def hash_password(self, plain_password: str) -> str:
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except ValueError:
            return False


class Md5PasswordHasher:
    """VULNERABLE (A04): MD5 is a fast hash, not a password KDF.

    PLAN FIX (A04): replace with Argon2id (preferred) or strong bcrypt via the
    ``PasswordHasher`` port; never store unsalted MD5/SHA-1 digests.
    """

    def hash_password(self, plain_password: str) -> str:
        # nosec B324 - intentional weak digest for iter-07 red-phase narrative
        return hashlib.md5(plain_password.encode("utf-8")).hexdigest()  # noqa: S324

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        return self.hash_password(plain_password) == password_hash


def build_password_hasher() -> PasswordHasher:
    """Return the process password hasher used by DI and seeding.

    VULNERABLE (A04): returns MD5 for the red-phase vulnerable tag.
    PLAN FIX (A04): return an Argon2id (or bcrypt) hasher and re-hash seeded
    credentials; manage pepper/KEK material via secret management.
    """
    return Md5PasswordHasher()
