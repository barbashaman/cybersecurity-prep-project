"""Security-related application ports."""

from __future__ import annotations

from typing import Protocol

from ecommerce_backoffice_api.domain.enums import UserRole


class PasswordHasher(Protocol):
    """Hashes and verifies passwords (bcrypt in Phase 1b)."""

    def hash_password(self, plain_password: str) -> str:
        """Return a one-way hash of ``plain_password``."""
        ...

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        """Return True when ``plain_password`` matches ``password_hash``."""
        ...


class TokenClaims:
    """Decoded access-token claims used by the presentation layer."""

    __slots__ = ("email", "role", "user_id")

    def __init__(self, user_id: int, email: str, role: UserRole) -> None:
        self.user_id = user_id
        self.email = email
        self.role = role


class TokenService(Protocol):
    """Issues and validates bearer access tokens."""

    def issue_access_token(self, *, user_id: int, email: str, role: UserRole) -> str:
        """Return a signed access token for the given principal."""
        ...

    def parse_access_token(self, token: str) -> TokenClaims:
        """Decode and validate ``token``; raise on failure."""
        ...
