"""FastAPI dependency providers (composition helpers for the presentation layer)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from ecommerce_backoffice_api.application.ports.security import TokenService
from ecommerce_backoffice_api.application.use_cases.authentication import (
    AuthenticateUser,
    GetCurrentUserProfile,
)
from ecommerce_backoffice_api.application.use_cases.orders import (
    GetOrder,
    ListOrdersForStore,
    UpdateOrderStatus,
)
from ecommerce_backoffice_api.application.use_cases.products import (
    CreateProduct,
    GetProduct,
    ListProductsForStore,
    UpdateProduct,
)
from ecommerce_backoffice_api.application.use_cases.stores import CreateStore, GetStore, ListStores
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError
from ecommerce_backoffice_api.infrastructure.config import Settings
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStoreRepository,
    SqlAlchemyUserRepository,
)
from ecommerce_backoffice_api.infrastructure.security.password_hasher import BcryptPasswordHasher

_bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    """Return process settings attached during application lifespan."""
    return cast(Settings, request.app.state.settings)


def get_session_factory(request: Request) -> sessionmaker[Session]:
    """Return the SQLAlchemy session factory from application state."""
    return cast(sessionmaker[Session], request.app.state.session_factory)


def get_token_service(request: Request) -> TokenService:
    """Return the JWT token service from application state."""
    return cast(TokenService, request.app.state.token_service)


def get_session(
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> Iterator[Session]:
    """Yield a request-scoped SQLAlchemy session with commit/rollback."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> User:
    """Resolve the authenticated user from a Bearer access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = token_service.parse_access_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_repository = SqlAlchemyUserRepository(session)
    try:
        return GetCurrentUserProfile(user_repository).execute(user_id=claims.user_id)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_authenticate_user(
    session: Annotated[Session, Depends(get_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> AuthenticateUser:
    """Build the login use case for the current request."""
    return AuthenticateUser(
        user_repository=SqlAlchemyUserRepository(session),
        password_hasher=BcryptPasswordHasher(),
        token_service=token_service,
    )


def get_list_stores(session: Annotated[Session, Depends(get_session)]) -> ListStores:
    return ListStores(SqlAlchemyStoreRepository(session))


def get_get_store(session: Annotated[Session, Depends(get_session)]) -> GetStore:
    return GetStore(SqlAlchemyStoreRepository(session))


def get_create_store(session: Annotated[Session, Depends(get_session)]) -> CreateStore:
    return CreateStore(SqlAlchemyStoreRepository(session))


def get_list_products(session: Annotated[Session, Depends(get_session)]) -> ListProductsForStore:
    return ListProductsForStore(
        SqlAlchemyProductRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_create_product(session: Annotated[Session, Depends(get_session)]) -> CreateProduct:
    return CreateProduct(
        SqlAlchemyProductRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_get_product(session: Annotated[Session, Depends(get_session)]) -> GetProduct:
    return GetProduct(SqlAlchemyProductRepository(session))


def get_update_product(session: Annotated[Session, Depends(get_session)]) -> UpdateProduct:
    return UpdateProduct(SqlAlchemyProductRepository(session))


def get_list_orders(session: Annotated[Session, Depends(get_session)]) -> ListOrdersForStore:
    return ListOrdersForStore(
        SqlAlchemyOrderRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_get_order(session: Annotated[Session, Depends(get_session)]) -> GetOrder:
    return GetOrder(SqlAlchemyOrderRepository(session))


def get_update_order_status(session: Annotated[Session, Depends(get_session)]) -> UpdateOrderStatus:
    return UpdateOrderStatus(SqlAlchemyOrderRepository(session))
