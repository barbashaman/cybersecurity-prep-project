"""Revenue analytics routes (iter-10 A01)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ecommerce_backoffice_api.application.use_cases.revenue import GetStoreRevenue
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import DomainError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_current_user,
    get_store_revenue_use_case,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.revenue import StoreRevenueResponse

router = APIRouter(prefix="/stores", tags=["revenue"])


@router.get("/{store_public_id}/revenue", response_model=StoreRevenueResponse)
def read_store_revenue(
    store_public_id: str,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetStoreRevenue, Depends(get_store_revenue_use_case)],
) -> StoreRevenueResponse:
    try:
        revenue = use_case.execute(actor=actor, store_public_id=store_public_id)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return StoreRevenueResponse(
        store_public_id=revenue.store_public_id,
        store_name=revenue.store_name,
        total_orders=revenue.total_orders,
        paid_orders=revenue.paid_orders,
        gross_revenue_cents=revenue.gross_revenue_cents,
    )
