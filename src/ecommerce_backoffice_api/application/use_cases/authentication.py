"""Authentication and session use cases (iter-04 A07 — remediated).

Secure behaviour:
- failed login bursts are rate-limited / locked out
- logout revokes the presented bearer token
"""

from __future__ import annotations

from dataclasses import dataclass

from ecommerce_backoffice_api.application.ports.repositories import UserRepository
from ecommerce_backoffice_api.application.ports.security import PasswordHasher, TokenService
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError, RateLimitError

_MAX_FAILED_LOGINS_BEFORE_LOCKOUT = 5


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Outcome of a successful login."""

    access_token: str
    token_type: str
    role: UserRole
    user_id: int


class AuthenticateUser:
    """Verify credentials and issue an access token."""

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._failed_login_counts: dict[str, int] = {}

    def execute(self, *, email: str, password: str) -> LoginResult:
        normalized_email = email.strip().lower()
        failed_count = self._failed_login_counts.get(normalized_email, 0)
        if failed_count >= _MAX_FAILED_LOGINS_BEFORE_LOCKOUT:
            raise RateLimitError("Too many failed login attempts. Try again later.")

        user = self._user_repository.get_by_email(normalized_email)
        if user is None or user.id is None:
            self._failed_login_counts[normalized_email] = failed_count + 1
            raise AuthenticationError("Invalid email or password.")
        if not self._password_hasher.verify_password(password, user.password_hash):
            self._failed_login_counts[normalized_email] = failed_count + 1
            raise AuthenticationError("Invalid email or password.")

        self._failed_login_counts.pop(normalized_email, None)
        token = self._token_service.issue_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )
        return LoginResult(
            access_token=token,
            token_type="bearer",  # nosec B106  # noqa: S106 - OAuth token_type, not a password
            role=user.role,
            user_id=user.id,
        )


class GetCurrentUserProfile:
    """Return the authenticated principal from the repository."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    def execute(self, *, user_id: int) -> User:
        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("Authenticated user no longer exists.")
        return user


class LogoutUser:
    """End an authenticated session by revoking the presented bearer token."""

    def __init__(self, token_service: TokenService) -> None:
        self._token_service = token_service

    def execute(self, *, access_token: str) -> None:
        self._token_service.revoke_access_token(access_token)
