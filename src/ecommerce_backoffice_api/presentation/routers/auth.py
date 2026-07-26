"""Authentication routes under ``/api/v1/auth``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ecommerce_backoffice_api.application.use_cases.authentication import AuthenticateUser
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError, DomainError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_authenticate_user,
    get_current_user,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
