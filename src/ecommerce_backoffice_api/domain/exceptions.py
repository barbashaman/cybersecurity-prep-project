"""Domain-level exceptions (framework-agnostic)."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain rule violations."""


class AuthenticationError(DomainError):
    """Raised when credentials are missing or invalid."""


class AuthorizationError(DomainError):
    """Raised when a principal is authenticated but not permitted."""


class NotFoundError(DomainError):
    """Raised when a requested aggregate cannot be found."""


class ConflictError(DomainError):
    """Raised when a write would violate a uniqueness or state constraint."""
