"""Mock credits, coupons, and checkout use cases (iter-05 A06).

VULNERABLE (A06 Insecure Design): business rules that should be domain
invariants are missing — coupons are reusable, negative quantities are
accepted, and stock is decremented without an availability check (oversell /
race).

PLAN FIX (A06):
- Threat-model checkout as a sensitive business flow (coupon abuse, credit
  drain, inventory integrity).
- Enforce domain invariants: ``quantity > 0``, ``stock >= quantity``,
  single-use coupon redemption.
- Require client idempotency keys for checkout retries.
- Persist unique redemption rows and DB CHECK / atomic stock constraints
  (``SELECT FOR UPDATE`` or conditional ``UPDATE … WHERE stock >= :qty``).
"""

from __future__ import annotations

from ecommerce_backoffice_api.application.dto.checkout import (
    CheckoutResultView,
    CouponView,
    CreditBalanceView,
)
from ecommerce_backoffice_api.application.ports.repositories import (
    CouponRepository,
    CreditRepository,
    OrderRepository,
    ProductRepository,
    StoreRepository,
)
from ecommerce_backoffice_api.application.use_cases.orders import to_order_detail_view
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import (
    Coupon,
    CustomerCredit,
    Order,
    OrderLine,
    Product,
    User,
)
from ecommerce_backoffice_api.domain.enums import OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
)


def _coupon_view(coupon: Coupon) -> CouponView:
    if coupon.id is None:
        raise NotFoundError("Coupon is missing a persistent identifier.")
    return CouponView(
        id=coupon.id,
        store_id=coupon.store_id,
        code=coupon.code,
        discount_percent=coupon.discount_percent,
        is_active=coupon.is_active,
    )


class GrantCredits:
    """Grant mock purchase credits to a customer (unlimited demo faucet)."""

    def __init__(self, credit_repository: CreditRepository) -> None:
        self._credit_repository = credit_repository

    def execute(
        self,
        *,
        actor: User,
        user_id: int,
        amount_cents: int,
    ) -> CreditBalanceView:
        if not authorization.can_grant_credits(actor):
            raise AuthorizationError("Not permitted to grant credits.")
        if actor.role is UserRole.CUSTOMER and actor.id != user_id:
            raise AuthorizationError("Customers may only grant credits to themselves.")
        if amount_cents <= 0:
            raise ConflictError("Credit grant amount must be positive.")

        existing = self._credit_repository.get_for_user(user_id)
        if existing is None:
            saved = self._credit_repository.save(
                CustomerCredit(user_id=user_id, balance_cents=amount_cents)
            )
        else:
            existing.balance_cents += amount_cents
            saved = self._credit_repository.save(existing)
        return CreditBalanceView(user_id=saved.user_id, balance_cents=saved.balance_cents)


class CreateCoupon:
    """Create a store-scoped discount coupon."""

    def __init__(
        self,
        coupon_repository: CouponRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._coupon_repository = coupon_repository
        self._store_repository = store_repository

    def execute(
        self,
        *,
        actor: User,
        store_id: int,
        code: str,
        discount_percent: int,
    ) -> CouponView:
        if not authorization.can_manage_coupons(actor, store_id):
            raise AuthorizationError("Not permitted to manage coupons for this store.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")
        if not 1 <= discount_percent <= 100:
            raise ConflictError("Discount percent must be between 1 and 100.")
        normalized = code.strip().upper()
        if not normalized:
            raise ConflictError("Coupon code must not be empty.")
        if self._coupon_repository.get_by_code(store_id, normalized) is not None:
            raise ConflictError(f"Coupon code {normalized!r} already exists.")
        coupon = self._coupon_repository.add(
            Coupon(
                store_id=store_id,
                code=normalized,
                discount_percent=discount_percent,
                is_active=True,
            )
        )
        return _coupon_view(coupon)


class PlaceOrder:
    """Place a customer order, optionally applying a discount coupon.

    VULNERABLE (A06):
    1. Coupons are never marked redeemed — the same code can be reused forever.
    2. Negative (or zero) line quantities are accepted without invariant checks.
    3. Stock is decremented without an availability guard (oversell / race).
    """

    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
        credit_repository: CreditRepository,
        coupon_repository: CouponRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._order_repository = order_repository
        self._product_repository = product_repository
        self._credit_repository = credit_repository
        self._coupon_repository = coupon_repository
        self._store_repository = store_repository

    def execute(
        self,
        *,
        actor: User,
        store_id: int,
        lines: list[tuple[int, int]],
        shipping_address: str,
        coupon_code: str | None = None,
        idempotency_key: str | None = None,
    ) -> CheckoutResultView:
        # PLAN FIX (A06): honour ``idempotency_key`` — return the prior result
        # for duplicate submissions instead of creating another order.
        _ = idempotency_key

        if not authorization.can_place_order(actor, store_id):
            raise AuthorizationError("Not permitted to place orders for this store.")
        if actor.id is None:
            raise AuthorizationError("Authenticated actor is missing an identifier.")
        if self._store_repository.get_by_id(store_id) is None:
            raise NotFoundError(f"Store {store_id} was not found.")
        if not lines:
            raise ConflictError("Checkout requires at least one order line.")

        # VULNERABLE (A06): no ``quantity > 0`` domain invariant.
        resolved_products: list[tuple[Product, int]] = []
        for product_id, quantity in lines:
            product = self._product_repository.get_by_id(product_id)
            if product is None or product.store_id != store_id:
                raise NotFoundError(f"Product {product_id} was not found in store {store_id}.")
            if not product.is_active:
                raise ConflictError(f"Product {product_id} is not active.")
            resolved_products.append((product, quantity))

        applied_coupon: Coupon | None = None
        if coupon_code is not None and coupon_code.strip():
            applied_coupon = self._coupon_repository.get_by_code(
                store_id, coupon_code.strip().upper()
            )
            if applied_coupon is None or not applied_coupon.is_active:
                raise NotFoundError(f"Coupon {coupon_code!r} was not found.")
            # VULNERABLE (A06): redemption is never recorded or checked.
            # PLAN FIX: if has_been_redeemed(coupon.id): raise ConflictError;
            # after order persist, record_redemption(...).

        subtotal_cents = sum(
            product.price_cents * quantity for product, quantity in resolved_products
        )
        discount_cents = 0
        if applied_coupon is not None:
            discount_cents = (subtotal_cents * applied_coupon.discount_percent) // 100
        total_cents = max(0, subtotal_cents - discount_cents)

        credit = self._credit_repository.get_for_user(actor.id)
        balance = 0 if credit is None else credit.balance_cents
        if balance < total_cents:
            raise ConflictError("Insufficient mock credits for this checkout.")

        # VULNERABLE (A06): stock decremented with no availability check /
        # atomic constraint — concurrent checkouts oversell inventory.
        # PLAN FIX: reject when stock_quantity < quantity; decrement under a
        # row lock or conditional UPDATE; add CHECK (stock_quantity >= 0).
        for product, quantity in resolved_products:
            product.stock_quantity -= quantity
            self._product_repository.save(product)

        order = self._order_repository.add(
            Order(
                store_id=store_id,
                customer_user_id=actor.id,
                status=OrderStatus.PENDING,
                customer_email=actor.email,
                customer_full_name=actor.full_name,
                shipping_address=shipping_address.strip(),
                lines=[
                    OrderLine(
                        product_id=product.id if product.id is not None else 0,
                        quantity=quantity,
                        unit_price_cents=product.price_cents,
                    )
                    for product, quantity in resolved_products
                ],
            )
        )

        if credit is None:
            credit = CustomerCredit(user_id=actor.id, balance_cents=0)
        credit.balance_cents -= total_cents
        self._credit_repository.save(credit)

        return CheckoutResultView(
            order=to_order_detail_view(order),
            subtotal_cents=subtotal_cents,
            discount_cents=discount_cents,
            total_cents=total_cents,
            coupon_code=applied_coupon.code if applied_coupon is not None else None,
            credits_charged_cents=total_cents,
        )


class ApplyCouponToOrder:
    """Apply a discount coupon to an existing order (reuse vehicle).

    VULNERABLE (A06): does not consult or write a redemption ledger, so the
    same coupon can be applied repeatedly across orders.
    """

    def __init__(
        self,
        order_repository: OrderRepository,
        coupon_repository: CouponRepository,
    ) -> None:
        self._order_repository = order_repository
        self._coupon_repository = coupon_repository

    def execute(
        self,
        *,
        actor: User,
        order_id: int,
        coupon_code: str,
    ) -> CheckoutResultView:
        order = self._order_repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        if not authorization.can_read_order(actor, order):
            raise AuthorizationError("Not permitted to apply a coupon to this order.")

        coupon = self._coupon_repository.get_by_code(order.store_id, coupon_code.strip().upper())
        if coupon is None or not coupon.is_active:
            raise NotFoundError(f"Coupon {coupon_code!r} was not found.")
        # VULNERABLE (A06): no single-use / redemption tracking.
        # PLAN FIX: reject when has_been_redeemed; record_redemption after apply.

        subtotal_cents = sum(line.unit_price_cents * line.quantity for line in order.lines)
        discount_cents = (subtotal_cents * coupon.discount_percent) // 100
        total_cents = max(0, subtotal_cents - discount_cents)
        return CheckoutResultView(
            order=to_order_detail_view(order),
            subtotal_cents=subtotal_cents,
            discount_cents=discount_cents,
            total_cents=total_cents,
            coupon_code=coupon.code,
            credits_charged_cents=0,
        )
