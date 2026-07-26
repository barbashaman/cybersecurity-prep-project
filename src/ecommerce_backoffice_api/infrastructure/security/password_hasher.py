"""Password hasher adapters implementing the application port.

iter-07 (A04) remediation uses Argon2id. The intentional MD5 hasher remains in
the repository history on ``iter-07-a04-vulnerable`` for red-phase demos.
"""

from __future__ import annotations

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerifyMismatchError

from ecommerce_backoffice_api.application.ports.security import PasswordHasher


class Argon2PasswordHasher:
    """Hash and verify passwords with Argon2id."""

    def __init__(self) -> None:
        self._hasher = Argon2Hasher()

    def hash_password(self, plain_password: str) -> str:
        return self._hasher.hash(plain_password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, plain_password)
        except VerifyMismatchError:
            return False
        except (ValueError, TypeError):
            return False


def build_password_hasher() -> PasswordHasher:
    """Return the process password hasher used by DI and seeding."""
    return Argon2PasswordHasher()
