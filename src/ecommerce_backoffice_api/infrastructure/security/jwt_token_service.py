"""JWT access-token service implementing the application port."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt

from ecommerce_backoffice_api.application.ports.security import TokenClaims
from ecommerce_backoffice_api.domain.enums import UserRole
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError


class JwtTokenService:
    """Issue and parse HS256 JWT access tokens."""

    def __init__(self, *, secret: str, algorithm: str, expire_minutes: int) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def issue_access_token(self, *, user_id: int, email: str, role: UserRole) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "role": role.value,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def parse_access_token(self, token: str) -> TokenClaims:
        try:
            payload = cast(
                dict[str, Any],
                jwt.decode(token, self._secret, algorithms=[self._algorithm]),
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid or expired access token.") from exc

        subject = payload.get("sub")
        email = payload.get("email")
        role_value = payload.get("role")
        if (
            not isinstance(subject, str)
            or not isinstance(email, str)
            or not isinstance(role_value, str)
        ):
            raise AuthenticationError("Access token is missing required claims.")
        try:
            user_id = int(subject)
            role = UserRole(role_value)
        except (TypeError, ValueError) as exc:
            raise AuthenticationError("Access token claims are malformed.") from exc
        return TokenClaims(user_id=user_id, email=email, role=role)
