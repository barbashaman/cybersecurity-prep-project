"""Idempotent deterministic seeder for the Phase 1b baseline.

Skips all work when the admin user already exists so migrate+seed is safe to
run on every API startup.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.seeding.constants import (
    ADMIN_EMAIL,
    CUSTOMER_ONE_EMAIL,
    CUSTOMER_TWO_EMAIL,
    DELIVERY_MANAGER_EMAIL,
    DEMO_ONLY_SEED_PASSWORD,
    OWNER_ONE_EMAIL,
    OWNER_TWO_EMAIL,
    STORE_ONE_NAME,
    STORE_TWO_NAME,
)
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.infrastructure.persistence.models import (
    CouponModel,
    CustomerCreditModel,
    OrderLineModel,
    OrderModel,
    ProductModel,
    StoreModel,
    UserModel,
)
from ecommerce_backoffice_api.infrastructure.security.password_hasher import (
    build_password_hasher,
)

logger = logging.getLogger(__name__)


def _product_catalog(store_name: str) -> list[tuple[str, str, int]]:
    """Return at least ten deterministic products for ``store_name``."""
    prefix = "NW" if "Northwind" in store_name else "CG"
    return [
        (f"{prefix} Trail Backpack", "Durable daypack for daily carry.", 8999),
        (f"{prefix} Softshell Jacket", "Wind-resistant layer for cool weather.", 12999),
        (f"{prefix} Merino Beanie", "Warm knit cap for outdoor use.", 2499),
        (f"{prefix} Insulated Bottle", "Keeps drinks cold for hours.", 3299),
        (f"{prefix} Camp Lantern", "USB-rechargeable lantern.", 4599),
        (f"{prefix} Hiking Poles", "Adjustable aluminum poles.", 5999),
        (f"{prefix} Field Notebook", "Weather-resistant notebook.", 1499),
        (f"{prefix} Canvas Tote", "Everyday tote with reinforced handles.", 2799),
        (f"{prefix} Desk Organizer", "Compact organizer for small parts.", 1999),
        (f"{prefix} USB-C Hub", "Four-port hub for laptops.", 4999),
        (f"{prefix} Wireless Mouse", "Quiet click office mouse.", 3499),
        (f"{prefix} Cable Pack", "Assorted charging cables.", 1799),
    ]


def seed_database(session: Session) -> bool:
    """Seed the baseline dataset.

    Returns True when seeding ran, False when it was skipped as already present.
    """
    existing_admin = session.scalars(
        select(UserModel).where(UserModel.email == ADMIN_EMAIL)
    ).first()
    if existing_admin is not None:
        logger.info("Seed skipped: admin user already present.")
        return False

    # VULNERABLE (A04): seed uses the process hasher (MD5 in red phase).
    hasher = build_password_hasher()
    password_hash = hasher.hash_password(DEMO_ONLY_SEED_PASSWORD)

    admin = UserModel(
        email=ADMIN_EMAIL,
        password_hash=password_hash,
        role=UserRole.ADMIN.value,
        full_name="Ada Admin",
        store_id=None,
    )
    delivery = UserModel(
        email=DELIVERY_MANAGER_EMAIL,
        password_hash=password_hash,
        role=UserRole.DELIVERY_MANAGER.value,
        full_name="Dana Delivery",
        store_id=None,
    )
    session.add_all([admin, delivery])
    session.flush()

    store_one = StoreModel(name=STORE_ONE_NAME, owner_user_id=None)
    store_two = StoreModel(name=STORE_TWO_NAME, owner_user_id=None)
    session.add_all([store_one, store_two])
    session.flush()

    owner_one = UserModel(
        email=OWNER_ONE_EMAIL,
        password_hash=password_hash,
        role=UserRole.STORE_OWNER.value,
        full_name="Olivia Owner",
        store_id=store_one.id,
    )
    owner_two = UserModel(
        email=OWNER_TWO_EMAIL,
        password_hash=password_hash,
        role=UserRole.STORE_OWNER.value,
        full_name="Owen Owner",
        store_id=store_two.id,
    )
    customer_one = UserModel(
        email=CUSTOMER_ONE_EMAIL,
        password_hash=password_hash,
        role=UserRole.CUSTOMER.value,
        full_name="Carla Customer",
        store_id=store_one.id,
    )
    customer_two = UserModel(
        email=CUSTOMER_TWO_EMAIL,
        password_hash=password_hash,
        role=UserRole.CUSTOMER.value,
        full_name="Chris Customer",
        store_id=store_two.id,
    )
    session.add_all([owner_one, owner_two, customer_one, customer_two])
    session.flush()

    store_one.owner_user_id = owner_one.id
    store_two.owner_user_id = owner_two.id
    session.flush()

    products_by_store: dict[int, list[ProductModel]] = {}
    for store in (store_one, store_two):
        products: list[ProductModel] = []
        for index, (name, description, price_cents) in enumerate(_product_catalog(store.name)):
            # First SKU per store has stock=1 to exercise oversell demos.
            stock = 1 if index == 0 else 25
            product = ProductModel(
                store_id=store.id,
                name=name,
                description=description,
                price_cents=price_cents,
                is_active=True,
                stock_quantity=stock,
            )
            products.append(product)
        session.add_all(products)
        session.flush()
        products_by_store[store.id] = products

    session.add_all(
        [
            CustomerCreditModel(user_id=customer_one.id, balance_cents=500_000),
            CustomerCreditModel(user_id=customer_two.id, balance_cents=500_000),
            CouponModel(
                store_id=store_one.id,
                code="SAVE10",
                discount_percent=10,
                is_active=True,
            ),
            CouponModel(
                store_id=store_two.id,
                code="SAVE10",
                discount_percent=10,
                is_active=True,
            ),
        ]
    )

    staged_statuses = (
        OrderStatus.PENDING,
        OrderStatus.CONFIRMED,
        OrderStatus.PACKED,
        OrderStatus.IN_TRANSIT,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    )
    order_specs: list[tuple[StoreModel, UserModel, OrderStatus, str, str]] = [
        (
            store_one,
            customer_one,
            staged_statuses[0],
            "12 Pine Street, Seattle, WA",
            "+1-206-555-0101",
        ),
        (
            store_one,
            customer_one,
            staged_statuses[2],
            "12 Pine Street, Seattle, WA",
            "+1-206-555-0101",
        ),
        (
            store_one,
            customer_one,
            staged_statuses[3],
            "45 Harbor Ave, Seattle, WA",
            "+1-206-555-0145",
        ),
        (
            store_two,
            customer_two,
            staged_statuses[1],
            "88 Market Road, Austin, TX",
            "+1-512-555-0188",
        ),
        (
            store_two,
            customer_two,
            staged_statuses[3],
            "88 Market Road, Austin, TX",
            "+1-512-555-0188",
        ),
        (
            store_two,
            customer_two,
            staged_statuses[4],
            "3 River Lane, Austin, TX",
            "+1-512-555-0103",
        ),
        (
            store_two,
            customer_two,
            staged_statuses[5],
            "3 River Lane, Austin, TX",
            "+1-512-555-0103",
        ),
    ]

    for store, customer, status, address, phone in order_specs:
        catalog = products_by_store[store.id]
        first = catalog[0]
        second = catalog[1]
        order = OrderModel(
            store_id=store.id,
            customer_user_id=customer.id,
            status=status.value,
            customer_email=customer.email,
            customer_full_name=customer.full_name,
            shipping_address=address,
            # VULNERABLE (A04): plaintext phone at rest (demo seed).
            customer_phone=phone,
            lines=[
                OrderLineModel(
                    product_id=first.id,
                    quantity=1,
                    unit_price_cents=first.price_cents,
                ),
                OrderLineModel(
                    product_id=second.id,
                    quantity=2,
                    unit_price_cents=second.price_cents,
                ),
            ],
        )
        session.add(order)

    session.flush()
    logger.info("Deterministic Phase 1b seed completed.")
    return True
