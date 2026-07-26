"""Checkout routes under ``/api/v1`` (iter-05 A06 vehicle)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ecommerce_backoffice_api.application.dto.checkout import CheckoutResultView
from ecommerce_backoffice_api.application.use_cases.checkout import ApplyCouponToOrder, PlaceOrder
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import DomainError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_apply_coupon_to_order,
    get_current_user,
    get_place_order,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.checkout import (
    ApplyCouponRequest,
    CheckoutRequest,
    CheckoutResponse,
)
from ecommerce_backoffice_api.presentation.schemas.orders import OrderLineResponse, OrderResponse

router = APIRouter(tags=["checkout"])


def _serialize_checkout(view: CheckoutResultView) -> CheckoutResponse:
    order = view.order
    return CheckoutResponse(
        order=OrderResponse(
            id=order.id,
            store_id=order.store_id,
            customer_user_id=order.customer_user_id,
            status=order.status,
            customer_email=order.customer_email,
            customer_full_name=order.customer_full_name,
            shipping_address=order.shipping_address,
            customer_phone=order.customer_phone,
            lines=[
                OrderLineResponse(
                    id=line.id,
                    product_id=line.product_id,
                    quantity=line.quantity,
                    unit_price_cents=line.unit_price_cents,
                )
                for line in order.lines
            ],
            notes=order.notes,
        ),
        subtotal_cents=view.subtotal_cents,
        discount_cents=view.discount_cents,
        total_cents=view.total_cents,
        coupon_code=view.coupon_code,
        credits_charged_cents=view.credits_charged_cents,
    )


@router.post(
    "/stores/{store_id}/orders/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout_order(
    store_id: int,
    payload: CheckoutRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[PlaceOrder, Depends(get_place_order)],
) -> CheckoutResponse:
    """Place an order with optional coupon.

    VULNERABLE (A06): accepts negative quantities, reusable coupons, and
    oversells stock (no availability check / race).
    """
    try:
        view = use_case.execute(
            actor=actor,
            store_id=store_id,
            lines=[(line.product_id, line.quantity) for line in payload.lines],
            shipping_address=payload.shipping_address,
            customer_phone=payload.customer_phone,
            coupon_code=payload.coupon_code,
            idempotency_key=payload.idempotency_key,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _serialize_checkout(view)


@router.post(
    "/orders/{order_id}/coupons/apply",
    response_model=CheckoutResponse,
)
def apply_coupon(
    order_id: int,
    payload: ApplyCouponRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ApplyCouponToOrder, Depends(get_apply_coupon_to_order)],
) -> CheckoutResponse:
    """Apply a discount coupon to an existing order.

    VULNERABLE (A06): coupons are not single-use — no redemption ledger check.
    """
    try:
        view = use_case.execute(
            actor=actor,
            order_id=order_id,
            coupon_code=payload.coupon_code,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _serialize_checkout(view)
