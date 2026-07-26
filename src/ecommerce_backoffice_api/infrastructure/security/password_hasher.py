"""bcrypt password hasher implementing the application port.

Argon2 and deliberately weak hashes are reserved for later OWASP iterations;
Phase 1b uses bcrypt only.
"""

from __future__ import annotations

import bcrypt


class BcryptPasswordHasher:
    """Hash and verify passwords with bcrypt."""

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
