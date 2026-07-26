"""Password-reset use cases (iter-04 A07 — remediated).

Secure behaviour:
- high-entropy, rotating, single-use reset tokens
- rate limiting on reset-request bursts
- short-lived session JWT after successful confirm
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from ecommerce_backoffice_api.application.ports.repositories import (
    PasswordResetTokenRepository,
    UserRepository,
)
from ecommerce_backoffice_api.application.ports.security import PasswordHasher, TokenService
from ecommerce_backoffice_api.domain.entities import PasswordResetToken
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

_MAX_RESET_REQUESTS_BEFORE_LOCKOUT = 5
_RESET_SESSION_EXPIRE_MINUTES = 15
_RESET_TOKEN_BYTE_LENGTH = 32


def predictable_reset_token_for_user(user_id: int) -> str:
    """Return the former red-phase predictable formula (used only by detection tests)."""
    return f"reset-token-for-user-{user_id}"


@dataclass(frozen=True, slots=True)
class PasswordResetRequestResult:
    """Outcome of a password-reset request (token exposed for the demo vehicle)."""

    reset_token: str
    user_id: int


@dataclass(frozen=True, slots=True)
class PasswordResetConfirmResult:
    """Outcome of a successful password-reset confirmation."""

    access_token: str
    token_type: str
    role: UserRole
    user_id: int


class RequestPasswordReset:
    """Issue a password-reset token for an account email."""

    def __init__(
        self,
        user_repository: UserRepository,
        reset_token_repository: PasswordResetTokenRepository,
    ) -> None:
        self._user_repository = user_repository
        self._reset_token_repository = reset_token_repository
        self._request_counts: dict[str, int] = {}

    def execute(self, *, email: str) -> PasswordResetRequestResult:
        normalized_email = email.strip().lower()
        attempt_count = self._request_counts.get(normalized_email, 0)
        if attempt_count >= _MAX_RESET_REQUESTS_BEFORE_LOCKOUT:
            raise RateLimitError("Too many password-reset requests. Try again later.")
        self._request_counts[normalized_email] = attempt_count + 1

        user = self._user_repository.get_by_email(normalized_email)
        if user is None or user.id is None:
            raise NotFoundError("No account matches that email.")

        self._reset_token_repository.delete_for_user(user.id)
        token = secrets.token_urlsafe(_RESET_TOKEN_BYTE_LENGTH)
        self._reset_token_repository.save(PasswordResetToken(user_id=user.id, token=token))
        return PasswordResetRequestResult(reset_token=token, user_id=user.id)


class ConfirmPasswordReset:
    """Confirm a password reset and issue a short-lived session access token."""

    def __init__(
        self,
        user_repository: UserRepository,
        reset_token_repository: PasswordResetTokenRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._reset_token_repository = reset_token_repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    def execute(self, *, token: str, new_password: str) -> PasswordResetConfirmResult:
        reset = self._reset_token_repository.get_by_token(token.strip())
        if reset is None:
            raise AuthenticationError("Invalid password-reset token.")
        user = self._user_repository.get_by_id(reset.user_id)
        if user is None or user.id is None:
            raise AuthenticationError("Invalid password-reset token.")
        password_hash = self._password_hasher.hash_password(new_password)
        updated = self._user_repository.update_password(user.id, password_hash)
        # Single-use: consume all outstanding reset tokens for this user.
        self._reset_token_repository.delete_for_user(user.id)
        access_token = self._token_service.issue_access_token(
            user_id=updated.id if updated.id is not None else user.id,
            email=updated.email,
            role=updated.role,
            expire_minutes=_RESET_SESSION_EXPIRE_MINUTES,
        )
        return PasswordResetConfirmResult(
            access_token=access_token,
            token_type="bearer",  # nosec B106  # noqa: S106 - OAuth token_type, not a password
            role=updated.role,
            user_id=updated.id if updated.id is not None else user.id,
        )
