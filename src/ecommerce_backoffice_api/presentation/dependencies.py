"""FastAPI dependency providers (composition helpers for the presentation layer)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from ecommerce_backoffice_api.application.ports.security import TokenService
from ecommerce_backoffice_api.application.use_cases.admin import ListAuditEvents, ListUsers
from ecommerce_backoffice_api.application.use_cases.audit import AdminAuditTrail
from ecommerce_backoffice_api.application.use_cases.authentication import (
    AuthenticateUser,
    GetCurrentUserProfile,
    LogoutUser,
)
from ecommerce_backoffice_api.application.use_cases.checkout import (
    ApplyCouponToOrder,
    CreateCoupon,
    GrantCredits,
    PlaceOrder,
)
from ecommerce_backoffice_api.application.use_cases.shipping_rates import GetShippingQuote
from ecommerce_backoffice_api.application.use_cases.orders import (
    GetOrder,
    ListOrdersForStore,
    UpdateOrderNotes,
    UpdateOrderStatus,
)
from ecommerce_backoffice_api.application.use_cases.password_reset import (
    ConfirmPasswordReset,
    RequestPasswordReset,
)
from ecommerce_backoffice_api.application.use_cases.products import (
    CreateProduct,
    GetProduct,
    ImportProductsFromCsv,
    ListProductsForStore,
    SearchProductsForStore,
    UpdateProduct,
)
from ecommerce_backoffice_api.application.use_cases.revenue import GetStoreRevenue
from ecommerce_backoffice_api.application.use_cases.receipts import (
    LoadOrderReceipt,
    StoreOrderReceipt,
)
from ecommerce_backoffice_api.application.use_cases.stores import CreateStore, GetStore, ListStores
from ecommerce_backoffice_api.application.use_cases.themes import GetStoreTheme, UploadStoreTheme
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import AuthenticationError
from ecommerce_backoffice_api.infrastructure.config import Settings
from ecommerce_backoffice_api.infrastructure.persistence.repositories import (
    SqlAlchemyAuditEventRepository,
    SqlAlchemyCouponRepository,
    SqlAlchemyCreditRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyPasswordResetTokenRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyReceiptRepository,
    SqlAlchemyStoreRepository,
    SqlAlchemyThemeRepository,
    SqlAlchemyUserRepository,
)
from ecommerce_backoffice_api.infrastructure.security.password_hasher import (
    build_password_hasher,
)
from ecommerce_backoffice_api.infrastructure.integrations.shipping import MockShippingRateProvider

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
        password_hasher=build_password_hasher(),
        token_service=token_service,
    )


def get_request_password_reset(
    session: Annotated[Session, Depends(get_session)],
) -> RequestPasswordReset:
    return RequestPasswordReset(
        user_repository=SqlAlchemyUserRepository(session),
        reset_token_repository=SqlAlchemyPasswordResetTokenRepository(session),
    )


def get_confirm_password_reset(
    session: Annotated[Session, Depends(get_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> ConfirmPasswordReset:
    return ConfirmPasswordReset(
        user_repository=SqlAlchemyUserRepository(session),
        reset_token_repository=SqlAlchemyPasswordResetTokenRepository(session),
        password_hasher=build_password_hasher(),
        token_service=token_service,
    )


def get_logout_user(
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> LogoutUser:
    return LogoutUser(token_service=token_service)


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


def get_search_products(
    session: Annotated[Session, Depends(get_session)],
) -> SearchProductsForStore:
    return SearchProductsForStore(
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


def get_admin_audit_trail(session: Annotated[Session, Depends(get_session)]) -> AdminAuditTrail:
    return AdminAuditTrail(SqlAlchemyAuditEventRepository(session))


def get_update_product(
    session: Annotated[Session, Depends(get_session)],
    admin_audit_trail: Annotated[AdminAuditTrail, Depends(get_admin_audit_trail)],
) -> UpdateProduct:
    return UpdateProduct(SqlAlchemyProductRepository(session), admin_audit_trail)


def get_import_products(session: Annotated[Session, Depends(get_session)]) -> ImportProductsFromCsv:
    return ImportProductsFromCsv(
        SqlAlchemyProductRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_list_orders(session: Annotated[Session, Depends(get_session)]) -> ListOrdersForStore:
    return ListOrdersForStore(
        SqlAlchemyOrderRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_get_order(
    session: Annotated[Session, Depends(get_session)],
    admin_audit_trail: Annotated[AdminAuditTrail, Depends(get_admin_audit_trail)],
) -> GetOrder:
    return GetOrder(SqlAlchemyOrderRepository(session), admin_audit_trail)


def get_update_order_status(session: Annotated[Session, Depends(get_session)]) -> UpdateOrderStatus:
    return UpdateOrderStatus(SqlAlchemyOrderRepository(session))


def get_update_order_notes(session: Annotated[Session, Depends(get_session)]) -> UpdateOrderNotes:
    return UpdateOrderNotes(SqlAlchemyOrderRepository(session))


def get_list_users(
    session: Annotated[Session, Depends(get_session)],
    admin_audit_trail: Annotated[AdminAuditTrail, Depends(get_admin_audit_trail)],
) -> ListUsers:
    return ListUsers(SqlAlchemyUserRepository(session), admin_audit_trail)


def get_list_audit_events(
    session: Annotated[Session, Depends(get_session)],
    admin_audit_trail: Annotated[AdminAuditTrail, Depends(get_admin_audit_trail)],
) -> ListAuditEvents:
    return ListAuditEvents(SqlAlchemyAuditEventRepository(session), admin_audit_trail)


def get_upload_store_theme(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> UploadStoreTheme:
    settings = cast(Settings, request.app.state.settings)
    return UploadStoreTheme(
        SqlAlchemyThemeRepository(session),
        SqlAlchemyStoreRepository(session),
        hmac_secret=settings.theme_hmac_secret,
    )


def get_get_store_theme(session: Annotated[Session, Depends(get_session)]) -> GetStoreTheme:
    return GetStoreTheme(
        SqlAlchemyThemeRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_store_order_receipt(session: Annotated[Session, Depends(get_session)]) -> StoreOrderReceipt:
    return StoreOrderReceipt(
        SqlAlchemyReceiptRepository(session),
        SqlAlchemyOrderRepository(session),
    )


def get_load_order_receipt(session: Annotated[Session, Depends(get_session)]) -> LoadOrderReceipt:
    return LoadOrderReceipt(
        SqlAlchemyReceiptRepository(session),
        SqlAlchemyOrderRepository(session),
    )


def get_grant_credits(session: Annotated[Session, Depends(get_session)]) -> GrantCredits:
    return GrantCredits(SqlAlchemyCreditRepository(session))


def get_create_coupon(session: Annotated[Session, Depends(get_session)]) -> CreateCoupon:
    return CreateCoupon(
        SqlAlchemyCouponRepository(session),
        SqlAlchemyStoreRepository(session),
    )


def get_place_order(session: Annotated[Session, Depends(get_session)]) -> PlaceOrder:
    return PlaceOrder(
        order_repository=SqlAlchemyOrderRepository(session),
        product_repository=SqlAlchemyProductRepository(session),
        credit_repository=SqlAlchemyCreditRepository(session),
        coupon_repository=SqlAlchemyCouponRepository(session),
        store_repository=SqlAlchemyStoreRepository(session),
    )


def get_apply_coupon_to_order(
    session: Annotated[Session, Depends(get_session)],
) -> ApplyCouponToOrder:
    return ApplyCouponToOrder(
        order_repository=SqlAlchemyOrderRepository(session),
        coupon_repository=SqlAlchemyCouponRepository(session),
    )


def get_shipping_quote_use_case() -> GetShippingQuote:
    return GetShippingQuote(provider=MockShippingRateProvider())


def get_store_revenue_use_case(
    session: Annotated[Session, Depends(get_session)],
) -> GetStoreRevenue:
    return GetStoreRevenue(
        store_repository=SqlAlchemyStoreRepository(session),
        order_repository=SqlAlchemyOrderRepository(session),
    )
