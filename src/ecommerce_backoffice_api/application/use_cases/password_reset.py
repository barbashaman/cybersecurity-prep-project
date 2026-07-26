"""Password-reset use cases (iter-04 A07 vehicle).

VULNERABLE (red phase):
- reset tokens are derived from the user id (predictable / replayable)
- no rate limiting on reset requests
- successful confirm issues a session JWT with no ``exp`` claim
- reset tokens are never expired or rotated after use

Remediation plan (not implemented here):
- issue short-lived, high-entropy rotating reset tokens (single-use)
- enforce lockout / rate limits on login and reset-request bursts
- maintain a token revocation list and invalidate sessions on logout
"""

from __future__ import annotations

from dataclasses import dataclass

from ecommerce_backoffice_api.application.ports.repositories import (
    PasswordResetTokenRepository,
    UserRepository,
)
from ecommerce_backoffice_api.application.ports.security import PasswordHasher, TokenService
from ecommerce_backoffice_api.domain.entities import PasswordResetToken
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError, NotFoundError

# Deliberately non-expiring session after password reset (A07).
_RESET_SESSION_EXPIRE_MINUTES = 0


def predictable_reset_token_for_user(user_id: int) -> str:
    """Return the red-phase predictable reset token formula for ``user_id``."""
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

    def execute(self, *, email: str) -> PasswordResetRequestResult:
        # VULNERABLE (A07): no rate limiting / lockout on repeated requests.
        user = self._user_repository.get_by_email(email.strip().lower())
        if user is None or user.id is None:
            raise NotFoundError("No account matches that email.")
        # VULNERABLE (A07): token is a stable, guessable function of user id.
        token = predictable_reset_token_for_user(user.id)
        self._reset_token_repository.save(
            PasswordResetToken(user_id=user.id, token=token)
        )
        return PasswordResetRequestResult(reset_token=token, user_id=user.id)


class ConfirmPasswordReset:
    """Confirm a password reset and issue a session access token."""

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
        # VULNERABLE (A07): reset token is not consumed / rotated after use.
        # VULNERABLE (A07): session JWT is issued with no expiry claim.
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
