"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_backoffice_api.domain.enums import UserRole


class LoginRequest(BaseModel):
    """Credentials submitted to ``POST /auth/login``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    """Access token envelope returned after a successful login."""

    access_token: str
    token_type: str
    role: UserRole
    user_id: int


class CurrentUserResponse(BaseModel):
    """Authenticated principal profile."""

    id: int
    email: str
    role: UserRole
    full_name: str
    store_id: int | None


class PasswordResetRequestBody(BaseModel):
    """Body for ``POST /auth/password-reset/request``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=320)


class PasswordResetRequestResponse(BaseModel):
    """Reset-request acknowledgement (includes token in the red-phase demo)."""

    message: str
    reset_token: str
    user_id: int


class PasswordResetConfirmBody(BaseModel):
    """Body for ``POST /auth/password-reset/confirm``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    token: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=1)


class PasswordResetConfirmResponse(BaseModel):
    """Session issued after a successful password reset."""

    access_token: str
    token_type: str
    role: UserRole
    user_id: int


class LogoutResponse(BaseModel):
    """Acknowledgement for ``POST /auth/logout``."""

    message: str
