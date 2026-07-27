"""Mock credit routes under ``/api/v1`` (iter-05 A06 vehicle)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ecommerce_backoffice_api.application.use_cases.checkout import GrantCredits
from ecommerce_backoffice_api.domain.entities import User
from ecommerce_backoffice_api.domain.exceptions import DomainError
from ecommerce_backoffice_api.presentation.dependencies import get_current_user, get_grant_credits
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.checkout import (
    CreditBalanceResponse,
    CreditGrantRequest,
)

router = APIRouter(prefix="/credits", tags=["credits"])


@router.post(
    "/grant",
    response_model=CreditBalanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def grant_credits(
    payload: CreditGrantRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GrantCredits, Depends(get_grant_credits)],
) -> CreditBalanceResponse:
    """Grant unlimited mock purchase credits (demo faucet)."""
    try:
        view = use_case.execute(
            actor=actor,
            user_id=payload.user_id,
            amount_cents=payload.amount_cents,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return CreditBalanceResponse(user_id=view.user_id, balance_cents=view.balance_cents)
