"""Order routes under ``/api/v1``."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ecommerce_backoffice_api.application.dto.orders import AnonymizedOrderView, OrderDetailView
from ecommerce_backoffice_api.application.use_cases.orders import (
    GetOrder,
    ListOrdersForStore,
    UpdateOrderStatus,
)
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import DomainError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_current_user,
    get_get_order,
    get_list_orders,
    get_update_order_status,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.orders import (
    AnonymizedOrderResponse,
    OrderLineResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
)

router = APIRouter(tags=["orders"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials


def _serialize_order(view: OrderDetailView | AnonymizedOrderView) -> dict[str, Any]:
    lines = [
        OrderLineResponse(
            id=line.id,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price_cents=line.unit_price_cents,
        )
        for line in view.lines
    ]
    if isinstance(view, AnonymizedOrderView):
        return AnonymizedOrderResponse(
            id=view.id,
            store_id=view.store_id,
            status=view.status,
            lines=lines,
        ).model_dump()
    return OrderResponse(
        id=view.id,
        store_id=view.store_id,
        customer_user_id=view.customer_user_id,
        status=view.status,
        customer_email=view.customer_email,
        customer_full_name=view.customer_full_name,
        shipping_address=view.shipping_address,
        lines=lines,
    ).model_dump()


@router.get("/stores/{store_id}/orders")
def list_orders(
    store_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListOrdersForStore, Depends(get_list_orders)],
) -> list[dict[str, Any]]:
    try:
        orders = use_case.execute(actor=actor, store_id=store_id)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return [_serialize_order(order) for order in orders]


@router.get("/orders/{order_id}")
def read_order(
    order_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetOrder, Depends(get_get_order)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> dict[str, Any]:
    try:
        order = use_case.execute(
            actor=actor,
            order_id=order_id,
            access_token=_access_token(credentials),
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _serialize_order(order)


@router.patch("/orders/{order_id}/status")
def patch_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[UpdateOrderStatus, Depends(get_update_order_status)],
) -> dict[str, Any]:
    try:
        order = use_case.execute(actor=actor, order_id=order_id, status=payload.status)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _serialize_order(order)
