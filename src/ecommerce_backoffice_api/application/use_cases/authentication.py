"""Authentication use cases."""

from __future__ import annotations

from dataclasses import dataclass

from ecommerce_backoffice_api.application.ports.repositories import UserRepository
from ecommerce_backoffice_api.application.ports.security import PasswordHasher, TokenService
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError


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

    def execute(self, *, email: str, password: str) -> LoginResult:
        user = self._user_repository.get_by_email(email.strip().lower())
        if user is None or user.id is None:
            raise AuthenticationError("Invalid email or password.")
        if not self._password_hasher.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")
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
