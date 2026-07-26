"""Coupon routes under ``/api/v1`` (iter-05 A06 vehicle)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ecommerce_backoffice_api.application.use_cases.checkout import CreateCoupon
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import DomainError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_create_coupon,
    get_current_user,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.checkout import (
    CouponCreateRequest,
    CouponResponse,
)

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(
    payload: CouponCreateRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[CreateCoupon, Depends(get_create_coupon)],
) -> CouponResponse:
    """Create a store-scoped discount coupon (admin / store owner)."""
    try:
        view = use_case.execute(
            actor=actor,
            store_id=payload.store_id,
            code=payload.code,
            discount_percent=payload.discount_percent,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return CouponResponse(
        id=view.id,
        store_id=view.store_id,
        code=view.code,
        discount_percent=view.discount_percent,
        is_active=view.is_active,
    )
