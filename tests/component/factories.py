"""Deterministic builders for component (use-case) tests."""

from __future__ import annotations

from ecommerce_backoffice_api.domain.entities import Coupon, Order, OrderLine, Product, Store, User
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole


def make_user(
    *,
    user_id: int,
    role: UserRole,
    store_id: int | None = 1,
    email: str | None = None,
) -> User:
    return User(
        id=user_id,
        email=email or f"{role.value}-{user_id}@example.test",
        password_hash="unused",
        role=role,
        full_name=f"{role.value} {user_id}",
        store_id=store_id,
    )


def make_store(
    *,
    store_id: int = 1,
    public_id: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    name: str = "Northwind",
    owner_user_id: int = 11,
) -> Store:
    return Store(id=store_id, public_id=public_id, name=name, owner_user_id=owner_user_id)


def make_product(
    *,
    product_id: int = 1,
    store_id: int = 1,
    price_cents: int = 1000,
    stock_quantity: int = 10,
    is_active: bool = True,
    name: str = "Widget",
) -> Product:
    return Product(
        id=product_id,
        store_id=store_id,
        name=name,
        description="demo",
        price_cents=price_cents,
        is_active=is_active,
        stock_quantity=stock_quantity,
    )


def make_order(
    *,
    order_id: int = 100,
    store_id: int = 1,
    customer_user_id: int = 201,
    status: OrderStatus = OrderStatus.PENDING,
    unit_price_cents: int = 1000,
    quantity: int = 1,
) -> Order:
    return Order(
        id=order_id,
        store_id=store_id,
        customer_user_id=customer_user_id,
        status=status,
        customer_email="buyer@example.test",
        customer_full_name="Buyer Person",
        shipping_address="1 Demo Way",
        customer_phone="+1-555-0100",
        lines=[
            OrderLine(
                id=1,
                product_id=1,
                quantity=quantity,
                unit_price_cents=unit_price_cents,
                order_id=order_id,
            )
        ],
    )


def make_coupon(
    *,
    coupon_id: int = 1,
    store_id: int = 1,
    code: str = "SAVE10",
    discount_percent: int = 10,
) -> Coupon:
    return Coupon(
        id=coupon_id,
        store_id=store_id,
        code=code,
        discount_percent=discount_percent,
        is_active=True,
    )
