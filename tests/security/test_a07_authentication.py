"""Detection tests for OWASP A07 — Authentication Failures (iter-04).

These tests assert *secure* behaviour:
- password-reset tokens must be high-entropy and non-predictable
- logout must revoke the access token (subsequent use fails)
- login / password-reset request must rate-limit after a burst of attempts
- password-reset confirm must issue a short-lived session JWT (``exp`` present)

Against the deliberately vulnerable red-phase code they FAIL (red). After
remediation they PASS (green). They are intentionally outside the quality-gate
domain+toolkit subset so Phase 1b CI stays green until this suite is wired in.
"""

from __future__ import annotations

import jwt
import pytest

from ecommerce_backoffice_api.application.use_cases.authentication import (
    AuthenticateUser,
    LogoutUser,
)
from ecommerce_backoffice_api.application.use_cases.password_reset import (
    ConfirmPasswordReset,
    RequestPasswordReset,
    predictable_reset_token_for_user,
)
from ecommerce_backoffice_api.domain.entities import PasswordResetToken, User
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError, RateLimitError
from ecommerce_backoffice_api.infrastructure.security.jwt_token_service import JwtTokenService

pytestmark = pytest.mark.security

_MAX_AUTH_ATTEMPTS_BEFORE_LOCKOUT = 5
_MAX_RESET_SESSION_TTL_SECONDS = 15 * 60


class _FakePasswordHasher:
    def hash_password(self, plain_password: str) -> str:
        return f"hashed:{plain_password}"

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{plain_password}"


class _FakeUserRepository:
    def __init__(self, user: User) -> None:
        self._user = user

    def get_by_id(self, user_id: int) -> User | None:
        return self._user if self._user.id == user_id else None

    def get_by_email(self, email: str) -> User | None:
        if self._user.email == email.strip().lower():
            return self._user
        return None

    def list_all(self) -> list[User]:
        return [self._user]

    def add(self, user: User) -> User:
        return user

    def update_password(self, user_id: int, password_hash: str) -> User:
        if self._user.id != user_id:
            raise AuthenticationError("User not found.")
        self._user.password_hash = password_hash
        return self._user


class _FakeResetTokenRepository:
    def __init__(self) -> None:
        self.tokens: dict[str, PasswordResetToken] = {}
        self._next_id = 1

    def save(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        reset_token.id = self._next_id
        self._next_id += 1
        self.tokens[reset_token.token] = reset_token
        return reset_token

    def get_by_token(self, token: str) -> PasswordResetToken | None:
        return self.tokens.get(token)

    def delete_for_user(self, user_id: int) -> None:
        self.tokens = {
            value.token: value for value in self.tokens.values() if value.user_id != user_id
        }


def _user() -> User:
    return User(
        id=7,
        email="owner1@example.test",
        password_hash="hashed:ChangeMeDemoOnly!",
        role=UserRole.STORE_OWNER,
        full_name="Olivia Owner",
        store_id=1,
    )


def _token_service() -> JwtTokenService:
    return JwtTokenService(
        secret="test-only-a07-jwt-secret",
        algorithm="HS256",
        expire_minutes=60,
    )


def test_reset_token_must_not_be_predictable() -> None:
    """Secure: reset tokens must be high-entropy and differ across requests."""
    user = _user()
    assert user.id is not None
    reset_repo = _FakeResetTokenRepository()
    use_case = RequestPasswordReset(_FakeUserRepository(user), reset_repo)

    first = use_case.execute(email=user.email)
    second = use_case.execute(email=user.email)

    assert first.reset_token != second.reset_token, "reset tokens must rotate per request"
    assert first.reset_token != predictable_reset_token_for_user(user.id)
    assert len(first.reset_token) >= 32, "reset tokens must be high-entropy"


def test_logout_must_invalidate_access_token() -> None:
    """Secure: after logout, the presented bearer token must be rejected."""
    user = _user()
    assert user.id is not None
    token_service = _token_service()
    access_token = token_service.issue_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    LogoutUser(token_service).execute(access_token=access_token)

    with pytest.raises(AuthenticationError):
        token_service.parse_access_token(access_token)


def test_password_reset_request_must_rate_limit_after_burst() -> None:
    """Secure: repeated password-reset requests must eventually rate-limit."""
    user = _user()
    use_case = RequestPasswordReset(_FakeUserRepository(user), _FakeResetTokenRepository())

    for _ in range(_MAX_AUTH_ATTEMPTS_BEFORE_LOCKOUT):
        use_case.execute(email=user.email)

    with pytest.raises(RateLimitError):
        use_case.execute(email=user.email)


def test_login_must_rate_limit_after_failed_attempts() -> None:
    """Secure: repeated failed logins must eventually rate-limit / lock out."""
    user = _user()
    use_case = AuthenticateUser(
        _FakeUserRepository(user),
        _FakePasswordHasher(),
        _token_service(),
    )

    for _ in range(_MAX_AUTH_ATTEMPTS_BEFORE_LOCKOUT):
        with pytest.raises(AuthenticationError):
            use_case.execute(email=user.email, password="wrong-password")

    with pytest.raises(RateLimitError):
        use_case.execute(email=user.email, password="wrong-password")


def test_reset_confirm_must_issue_short_lived_session_token() -> None:
    """Secure: post-reset session JWTs must include a short ``exp`` claim."""
    user = _user()
    assert user.id is not None
    reset_repo = _FakeResetTokenRepository()
    reset_repo.save(
        PasswordResetToken(user_id=user.id, token="opaque-high-entropy-reset-token-value")
    )
    use_case = ConfirmPasswordReset(
        _FakeUserRepository(user),
        reset_repo,
        _FakePasswordHasher(),
        _token_service(),
    )

    result = use_case.execute(
        token="opaque-high-entropy-reset-token-value",
        new_password="BrandNewDemoOnly!",
    )
    claims = jwt.decode(result.access_token, options={"verify_signature": False})

    assert "exp" in claims, "session JWT after reset must expire"
    assert "iat" in claims
    assert int(claims["exp"]) - int(claims["iat"]) <= _MAX_RESET_SESSION_TTL_SECONDS
