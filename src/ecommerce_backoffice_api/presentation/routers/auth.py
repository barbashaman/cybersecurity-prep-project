"""Authentication routes under ``/api/v1/auth``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ecommerce_backoffice_api.application.use_cases.authentication import (
    AuthenticateUser,
    LogoutUser,
)
from ecommerce_backoffice_api.application.use_cases.password_reset import (
    ConfirmPasswordReset,
    RequestPasswordReset,
)
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError, DomainError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_authenticate_user,
    get_confirm_password_reset,
    get_current_user,
    get_logout_user,
    get_request_password_reset,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordResetConfirmBody,
    PasswordResetConfirmResponse,
    PasswordResetRequestBody,
    PasswordResetRequestResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    use_case: Annotated[AuthenticateUser, Depends(get_authenticate_user)],
) -> LoginResponse:
    try:
        result = use_case.execute(email=payload.email, password=payload.password)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return LoginResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        role=result.role,
        user_id=result.user_id,
    )


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
    actor: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    if actor.id is None:
        raise http_error_from_domain(AuthenticationError("Authenticated user is missing an id."))
    return CurrentUserResponse(
        id=actor.id,
        email=actor.email,
        role=actor.role,
        full_name=actor.full_name,
        store_id=actor.store_id,
    )


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
def request_password_reset(
    payload: PasswordResetRequestBody,
    use_case: Annotated[RequestPasswordReset, Depends(get_request_password_reset)],
) -> PasswordResetRequestResponse:
    # VULNERABLE (A07): no rate limiting at the edge; predictable token returned.
    try:
        result = use_case.execute(email=payload.email)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return PasswordResetRequestResponse(
        message="Password reset token issued.",
        reset_token=result.reset_token,
        user_id=result.user_id,
    )


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmBody,
    use_case: Annotated[ConfirmPasswordReset, Depends(get_confirm_password_reset)],
) -> PasswordResetConfirmResponse:
    # VULNERABLE (A07): confirm issues a non-expiring session JWT.
    try:
        result = use_case.execute(token=payload.token, new_password=payload.new_password)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return PasswordResetConfirmResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        role=result.role,
        user_id=result.user_id,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    use_case: Annotated[LogoutUser, Depends(get_logout_user)],
) -> LogoutResponse:
    # VULNERABLE (A07): logout is a no-op; the bearer token remains valid.
    token = credentials.credentials if credentials is not None else ""
    try:
        use_case.execute(access_token=token)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return LogoutResponse(message="Logged out.")
