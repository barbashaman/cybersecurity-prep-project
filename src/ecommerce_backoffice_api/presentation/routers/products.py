"""Product routes under ``/api/v1``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.datastructures import UploadFile

from ecommerce_backoffice_api.application.use_cases.products import (
    CreateProduct,
    GetProduct,
    ImportProductsFromCsv,
    ListProductsForStore,
    SearchProductsForStore,
    UpdateProduct,
)
from ecommerce_backoffice_api.domain.entities import Product, User
from ecommerce_backoffice_api.domain.exceptions import DomainError, NotFoundError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_create_product,
    get_current_user,
    get_get_product,
    get_import_products,
    get_list_products,
    get_search_products,
    get_update_product,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.products import (
    ProductCreateRequest,
    ProductImportResponse,
    ProductResponse,
    ProductSearchQuery,
    ProductUpdateRequest,
)

router = APIRouter(tags=["products"])
_bearer_scheme = HTTPBearer(auto_error=False)


def _access_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return credentials.credentials


def _product_response(product: Product) -> ProductResponse:
    if product.id is None:
        raise http_error_from_domain(NotFoundError("Product is missing a persistent identifier."))
    return ProductResponse(
        id=product.id,
        store_id=product.store_id,
        name=product.name,
        description=product.description,
        price_cents=product.price_cents,
        is_active=product.is_active,
        stock_quantity=product.stock_quantity,
    )


@router.get("/stores/{store_id}/products", response_model=list[ProductResponse])
def list_products(
    store_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListProductsForStore, Depends(get_list_products)],
) -> list[ProductResponse]:
    try:
        products = use_case.execute(actor=actor, store_id=store_id)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return [_product_response(product) for product in products if product.id is not None]


@router.get("/stores/{store_id}/products/search", response_model=list[ProductResponse])
def search_products(
    store_id: int,
    query: Annotated[ProductSearchQuery, Depends()],
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[SearchProductsForStore, Depends(get_search_products)],
) -> list[ProductResponse]:
    """Search products by name within a store.

    VULNERABLE (A05): ``q`` is concatenated into raw SQL in the repository.
    PLAN FIX (A05): parameterized queries + Pydantic validation on ``q``.
    """
    try:
        products = use_case.execute(actor=actor, store_id=store_id, query=query.q)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return [_product_response(product) for product in products if product.id is not None]


@router.post(
    "/stores/{store_id}/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    store_id: int,
    payload: ProductCreateRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[CreateProduct, Depends(get_create_product)],
) -> ProductResponse:
    try:
        product = use_case.execute(
            actor=actor,
            store_id=store_id,
            name=payload.name,
            description=payload.description,
            price_cents=payload.price_cents,
            is_active=payload.is_active,
            stock_quantity=payload.stock_quantity,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _product_response(product)


@router.get("/products/{product_id}", response_model=ProductResponse)
def read_product(
    product_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetProduct, Depends(get_get_product)],
) -> ProductResponse:
    try:
        product = use_case.execute(actor=actor, product_id=product_id)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _product_response(product)


@router.patch("/products/{product_id}", response_model=ProductResponse)
def patch_product(
    product_id: int,
    payload: ProductUpdateRequest,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[UpdateProduct, Depends(get_update_product)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> ProductResponse:
    try:
        product = use_case.execute(
            actor=actor,
            product_id=product_id,
            name=payload.name,
            description=payload.description,
            price_cents=payload.price_cents,
            is_active=payload.is_active,
            stock_quantity=payload.stock_quantity,
            access_token=_access_token(credentials),
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _product_response(product)


async def _read_csv_payload(request: Request) -> str:
    """Read CSV bytes from multipart ``file`` or a raw request body."""
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multipart import requires a 'file' field.",
            )
        csv_bytes = await upload.read()
        return csv_bytes.decode("utf-8")
    return (await request.body()).decode("utf-8")


@router.post(
    "/stores/{store_id}/products/import",
    response_model=ProductImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_products(
    store_id: int,
    request: Request,
    actor: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ImportProductsFromCsv, Depends(get_import_products)],
) -> ProductImportResponse:
    """Bulk-import products from CSV (multipart file or raw ``text/csv`` body).

    Domain errors are mapped to HTTP. All other exceptions (``KeyError``,
    ``ZeroDivisionError``, ...) propagate unhandled so the DEBUG exception
    handler can leak stack traces — the iter-01 A10 flaw.
    """
    csv_text = await _read_csv_payload(request)

    try:
        products = use_case.execute(actor=actor, store_id=store_id, csv_text=csv_text)
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return ProductImportResponse(
        imported_count=len(products),
        products=[_product_response(product) for product in products if product.id is not None],
    )
