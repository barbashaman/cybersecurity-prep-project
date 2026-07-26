"""Store routes under ``/api/v1/stores``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ecommerce_backoffice_api.application.use_cases.stores import CreateStore, GetStore, ListStores
from ecommerce_backoffice_api.domain.entities import Store, User
from ecommerce_backoffice_api.domain.exceptions import DomainError, NotFoundError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_create_store,
    get_current_user,
    get_get_store,
    get_list_stores,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.stores import StoreCreateRequest, StoreResponse

router = APIRouter(prefix="/stores", tags=["stores"])


def _store_response(store: Store) -> StoreResponse:
    if store.id is None:
        raise http_error_from_domain(NotFoundError("Store is missing a persistent identifier."))
    return StoreResponse(id=store.id, name=store.name, owner_user_id=store.owner_user_id)


@router.get("", response_model=list[StoreResponse])
def list_stores(
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListStores, Depends(get_list_stores)],
) -> list[StoreResponse]:
    try:
        stores = use_case.execute(actor=actor)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return [_store_response(store) for store in stores if store.id is not None]


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: StoreCreateRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[CreateStore, Depends(get_create_store)],
) -> StoreResponse:
    try:
        store = use_case.execute(
            actor=actor,
            name=payload.name,
            owner_user_id=payload.owner_user_id,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _store_response(store)


@router.get("/{store_id}", response_model=StoreResponse)
def read_store(
    store_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetStore, Depends(get_get_store)],
) -> StoreResponse:
    try:
        store = use_case.execute(actor=actor, store_id=store_id)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _store_response(store)
