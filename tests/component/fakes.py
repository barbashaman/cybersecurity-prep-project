"""In-memory fake ports for isolated component (use-case) tests."""

from __future__ import annotations

from ecommerce_backoffice_api.domain.entities import (
    AuditEvent,
    Coupon,
    CouponRedemption,
    CustomerCredit,
    Order,
    Product,
    Store,
)
from ecommerce_backoffice_api.domain.enums import OrderStatus
from ecommerce_backoffice_api.domain.exceptions import NotFoundError


class FakeStoreRepository:
    def __init__(self, stores: list[Store] | None = None) -> None:
        self._stores = list(stores or [])
        self._next_id = max((s.id or 0 for s in self._stores), default=0) + 1

    def list_all(self) -> list[Store]:
        return list(self._stores)

    def get_by_id(self, store_id: int) -> Store | None:
        for store in self._stores:
            if store.id == store_id:
                return store
        return None

    def get_by_public_id(self, public_id: str) -> Store | None:
        needle = public_id.strip().lower()
        for store in self._stores:
            if (store.public_id or "").lower() == needle:
                return store
        return None

    def add(self, store: Store) -> Store:
        if store.id is None:
            store.id = self._next_id
            self._next_id += 1
        self._stores.append(store)
        return store


class FakeProductRepository:
    def __init__(self, products: list[Product] | None = None) -> None:
        self._products = list(products or [])
        self._next_id = max((p.id or 0 for p in self._products), default=0) + 1

    def list_for_store(self, store_id: int) -> list[Product]:
        return [p for p in self._products if p.store_id == store_id]

    def search_for_store(self, store_id: int, query: str) -> list[Product]:
        needle = query.lower()
        return [
            p
            for p in self._products
            if p.store_id == store_id and needle in p.name.lower()
        ]

    def get_by_id(self, product_id: int) -> Product | None:
        for product in self._products:
            if product.id == product_id:
                return product
        return None

    def add(self, product: Product) -> Product:
        if product.id is None:
            product.id = self._next_id
            self._next_id += 1
        self._products.append(product)
        return product

    def save(self, product: Product) -> Product:
        if product.id is None:
            return self.add(product)
        for index, existing in enumerate(self._products):
            if existing.id == product.id:
                self._products[index] = product
                return product
        self._products.append(product)
        return product


class FakeOrderRepository:
    def __init__(self, orders: list[Order] | None = None) -> None:
        self._orders = list(orders or [])
        self._next_id = max((o.id or 0 for o in self._orders), default=0) + 1
        self._next_line_id = 1

    def list_for_store(self, store_id: int) -> list[Order]:
        return [o for o in self._orders if o.store_id == store_id]

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        return [
            o
            for o in self._orders
            if o.store_id == store_id and o.customer_user_id == customer_user_id
        ]

    def get_by_id(self, order_id: int) -> Order | None:
        for order in self._orders:
            if order.id == order_id:
                return order
        return None

    def add(self, order: Order) -> Order:
        if order.id is None:
            order.id = self._next_id
            self._next_id += 1
        for line in order.lines:
            if line.id is None:
                line.id = self._next_line_id
                self._next_line_id += 1
            line.order_id = order.id
        self._orders.append(order)
        return order

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        order = self.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        order.status = status
        return order

    def update_notes(self, order_id: int, notes: str) -> Order:
        order = self.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        order.notes = notes
        return order


class FakeCreditRepository:
    def __init__(self, credits: list[CustomerCredit] | None = None) -> None:
        self._credits = {c.user_id: c for c in (credits or [])}
        self._next_id = max((c.id or 0 for c in self._credits.values()), default=0) + 1

    def get_for_user(self, user_id: int) -> CustomerCredit | None:
        return self._credits.get(user_id)

    def save(self, credit: CustomerCredit) -> CustomerCredit:
        if credit.id is None:
            credit.id = self._next_id
            self._next_id += 1
        self._credits[credit.user_id] = credit
        return credit


class FakeCouponRepository:
    def __init__(self, coupons: list[Coupon] | None = None) -> None:
        self._coupons = list(coupons or [])
        self._redemptions: list[CouponRedemption] = []
        self._next_id = max((c.id or 0 for c in self._coupons), default=0) + 1
        self._next_redemption_id = 1

    def add(self, coupon: Coupon) -> Coupon:
        if coupon.id is None:
            coupon.id = self._next_id
            self._next_id += 1
        self._coupons.append(coupon)
        return coupon

    def get_by_code(self, store_id: int, code: str) -> Coupon | None:
        needle = code.strip().upper()
        for coupon in self._coupons:
            if coupon.store_id == store_id and coupon.code.upper() == needle:
                return coupon
        return None

    def record_redemption(self, redemption: CouponRedemption) -> CouponRedemption:
        if redemption.id is None:
            redemption.id = self._next_redemption_id
            self._next_redemption_id += 1
        self._redemptions.append(redemption)
        return redemption

    def has_been_redeemed(self, coupon_id: int) -> bool:
        return any(r.coupon_id == coupon_id for r in self._redemptions)


class FakeAuditEventRepository:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._next_id = 1

    def add(self, event: AuditEvent) -> AuditEvent:
        if event.id is None:
            event.id = self._next_id
            self._next_id += 1
        self.events.append(event)
        return event

    def list_recent(self, *, limit: int = 100) -> list[AuditEvent]:
        return list(reversed(self.events))[:limit]
