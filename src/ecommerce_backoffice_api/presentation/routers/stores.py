"""Store routes under ``/api/v1/stores``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, status

from ecommerce_backoffice_api.application.use_cases.stores import CreateStore, GetStore, ListStores
from ecommerce_backoffice_api.application.use_cases.themes import GetStoreTheme, UploadStoreTheme
from ecommerce_backoffice_api.domain.entities import Store, StoreTheme, User
from ecommerce_backoffice_api.domain.exceptions import DomainError, NotFoundError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_create_store,
    get_current_user,
    get_get_store,
    get_get_store_theme,
    get_list_stores,
    get_upload_store_theme,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.stores import StoreCreateRequest, StoreResponse
from ecommerce_backoffice_api.presentation.schemas.themes import StoreThemeResponse

router = APIRouter(prefix="/stores", tags=["stores"])


def _store_response(store: Store) -> StoreResponse:
    if store.id is None:
        raise http_error_from_domain(NotFoundError("Store is missing a persistent identifier."))
    return StoreResponse(id=store.id, name=store.name, owner_user_id=store.owner_user_id)


def _theme_response(theme: StoreTheme) -> StoreThemeResponse:
    if theme.id is None:
        raise http_error_from_domain(NotFoundError("Theme is missing a persistent identifier."))
    return StoreThemeResponse(
        id=theme.id,
        store_id=theme.store_id,
        content_type=theme.content_type,
        artifact_size_bytes=len(theme.artifact_bytes),
    )


async def _read_theme_artifact(request: Request) -> tuple[bytes, str]:
    """Read theme bytes from multipart ``file`` or a raw request body."""
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multipart theme upload requires a 'file' field.",
            )
        artifact_bytes = await upload.read()
        upload_content_type = upload.content_type or "application/octet-stream"
        return artifact_bytes, upload_content_type
    body_content_type = content_type.split(";")[0].strip() or "application/octet-stream"
    return await request.body(), body_content_type


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


@router.post(
    "/{store_id}/theme",
    response_model=StoreThemeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_store_theme(
    store_id: int,
    request: Request,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[UploadStoreTheme, Depends(get_upload_store_theme)],
    x_artifact_signature: Annotated[str | None, Header()] = None,
) -> StoreThemeResponse:
    """Upload a storefront theme artifact (multipart ``file`` or raw body).

    VULNERABLE (A08): ``X-Artifact-Signature`` is accepted but never verified, so
    unsigned theme artifacts are trusted and persisted.
    """
    artifact_bytes, content_type = await _read_theme_artifact(request)
    try:
        theme = use_case.execute(
            actor=actor,
            store_id=store_id,
            artifact_bytes=artifact_bytes,
            content_type=content_type,
            signature_hex=x_artifact_signature,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _theme_response(theme)


@router.get("/{store_id}/theme", response_model=StoreThemeResponse)
def read_store_theme(
    store_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetStoreTheme, Depends(get_get_store_theme)],
) -> StoreThemeResponse:
    try:
        theme = use_case.execute(actor=actor, store_id=store_id)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _theme_response(theme)
