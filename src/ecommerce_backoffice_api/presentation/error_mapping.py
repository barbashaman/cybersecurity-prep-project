"""Map domain exceptions to HTTP errors (no business rules here)."""

from __future__ import annotations

from fastapi import HTTPException, status

from ecommerce_backoffice_api.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    NotFoundError,
)


def http_error_from_domain(error: DomainError) -> HTTPException:
    """Translate a domain exception into an ``HTTPException``."""
    if isinstance(error, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        )
    if isinstance(error, AuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
