"""Product routes under ``/api/v1``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ecommerce_backoffice_api.application.use_cases.products import (
    CreateProduct,
    GetProduct,
    ListProductsForStore,
    UpdateProduct,
)
from ecommerce_backoffice_api.domain.entities import Product, User
from ecommerce_backoffice_api.domain.exceptions import DomainError, NotFoundError
from ecommerce_backoffice_api.presentation.dependencies import (
    get_create_product,
    get_current_user,
    get_get_product,
    get_list_products,
    get_update_product,
)
from ecommerce_backoffice_api.presentation.error_mapping import http_error_from_domain
from ecommerce_backoffice_api.presentation.schemas.products import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)

router = APIRouter(tags=["products"])


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
) -> ProductResponse:
    try:
        product = use_case.execute(
            actor=actor,
            product_id=product_id,
            name=payload.name,
            description=payload.description,
            price_cents=payload.price_cents,
            is_active=payload.is_active,
        )
    except DomainError as error:
        raise http_error_from_domain(error) from error
    return _product_response(product)
