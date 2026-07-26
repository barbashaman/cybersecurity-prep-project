"""SQLAlchemy repository adapters implementing application ports."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ecommerce_backoffice_api.domain.entities import (
    AuditEvent,
    Order,
    OrderLine,
    OrderReceipt,
    Product,
    Store,
    StoreTheme,
    User,
)
from ecommerce_backoffice_api.domain.enums import AuditOutcome, OrderStatus, UserRole
from ecommerce_backoffice_api.domain.exceptions import NotFoundError
from ecommerce_backoffice_api.infrastructure.persistence.models import (
    AuditEventModel,
    OrderLineModel,
    OrderModel,
    OrderReceiptModel,
    ProductModel,
    StoreModel,
    StoreThemeModel,
    UserModel,
)


def _user_from_model(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        role=UserRole(model.role),
        full_name=model.full_name,
        store_id=model.store_id,
    )


def _store_from_model(model: StoreModel) -> Store:
    return Store(id=model.id, name=model.name, owner_user_id=model.owner_user_id)


def _product_from_model(model: ProductModel) -> Product:
    return Product(
        id=model.id,
        store_id=model.store_id,
        name=model.name,
        description=model.description,
        price_cents=model.price_cents,
        is_active=model.is_active,
    )


def _order_from_model(model: OrderModel) -> Order:
    lines = [
        OrderLine(
            id=line.id,
            order_id=line.order_id,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price_cents=line.unit_price_cents,
        )
        for line in model.lines
    ]
    return Order(
        id=model.id,
        store_id=model.store_id,
        customer_user_id=model.customer_user_id,
        status=OrderStatus(model.status),
        customer_email=model.customer_email,
        customer_full_name=model.customer_full_name,
        shipping_address=model.shipping_address,
        lines=lines,
    )


def _audit_event_from_model(model: AuditEventModel) -> AuditEvent:
    return AuditEvent(
        id=model.id,
        actor_user_id=model.actor_user_id,
        action=model.action,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        outcome=AuditOutcome(model.outcome),
        detail=model.detail,
        created_at=model.created_at,
    )


def _store_theme_from_model(model: StoreThemeModel) -> StoreTheme:
    return StoreTheme(
        id=model.id,
        store_id=model.store_id,
        artifact_bytes=bytes(model.artifact_bytes),
        content_type=model.content_type,
    )


def _order_receipt_from_model(model: OrderReceiptModel) -> OrderReceipt:
    return OrderReceipt(
        id=model.id,
        order_id=model.order_id,
        payload_blob=bytes(model.payload_blob),
    )


class SqlAlchemyUserRepository:
    """User repository backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _user_from_model(model) if model is not None else None

    def get_by_email(self, email: str) -> User | None:
        statement = select(UserModel).where(UserModel.email == email.strip().lower())
        model = self._session.scalars(statement).first()
        return _user_from_model(model) if model is not None else None

    def list_all(self) -> list[User]:
        models = self._session.scalars(select(UserModel).order_by(UserModel.id)).all()
        return [_user_from_model(model) for model in models]

    def add(self, user: User) -> User:
        model = UserModel(
            email=user.email.strip().lower(),
            password_hash=user.password_hash,
            role=user.role.value,
            full_name=user.full_name,
            store_id=user.store_id,
        )
        self._session.add(model)
        self._session.flush()
        return _user_from_model(model)


class SqlAlchemyStoreRepository:
    """Store repository backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Store]:
        models = self._session.scalars(select(StoreModel).order_by(StoreModel.id)).all()
        return [_store_from_model(model) for model in models]

    def get_by_id(self, store_id: int) -> Store | None:
        model = self._session.get(StoreModel, store_id)
        return _store_from_model(model) if model is not None else None

    def add(self, store: Store) -> Store:
        model = StoreModel(name=store.name, owner_user_id=store.owner_user_id)
        self._session.add(model)
        self._session.flush()
        return _store_from_model(model)


class SqlAlchemyProductRepository:
    """Product repository backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_store(self, store_id: int) -> list[Product]:
        statement = (
            select(ProductModel).where(ProductModel.store_id == store_id).order_by(ProductModel.id)
        )
        return [_product_from_model(model) for model in self._session.scalars(statement).all()]

    def get_by_id(self, product_id: int) -> Product | None:
        model = self._session.get(ProductModel, product_id)
        return _product_from_model(model) if model is not None else None

    def add(self, product: Product) -> Product:
        model = ProductModel(
            store_id=product.store_id,
            name=product.name,
            description=product.description,
            price_cents=product.price_cents,
            is_active=product.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return _product_from_model(model)

    def save(self, product: Product) -> Product:
        if product.id is None:
            raise NotFoundError("Cannot save a product without an id.")
        model = self._session.get(ProductModel, product.id)
        if model is None:
            raise NotFoundError(f"Product {product.id} was not found.")
        model.name = product.name
        model.description = product.description
        model.price_cents = product.price_cents
        model.is_active = product.is_active
        self._session.flush()
        return _product_from_model(model)


class SqlAlchemyOrderRepository:
    """Order repository backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_store(self, store_id: int) -> list[Order]:
        statement = (
            select(OrderModel)
            .options(selectinload(OrderModel.lines))
            .where(OrderModel.store_id == store_id)
            .order_by(OrderModel.id)
        )
        return [_order_from_model(model) for model in self._session.scalars(statement).all()]

    def list_for_store_and_customer(self, store_id: int, customer_user_id: int) -> list[Order]:
        statement = (
            select(OrderModel)
            .options(selectinload(OrderModel.lines))
            .where(
                OrderModel.store_id == store_id,
                OrderModel.customer_user_id == customer_user_id,
            )
            .order_by(OrderModel.id)
        )
        return [_order_from_model(model) for model in self._session.scalars(statement).all()]

    def get_by_id(self, order_id: int) -> Order | None:
        statement = (
            select(OrderModel)
            .options(selectinload(OrderModel.lines))
            .where(OrderModel.id == order_id)
        )
        model = self._session.scalars(statement).first()
        return _order_from_model(model) if model is not None else None

    def add(self, order: Order) -> Order:
        model = OrderModel(
            store_id=order.store_id,
            customer_user_id=order.customer_user_id,
            status=order.status.value,
            customer_email=order.customer_email,
            customer_full_name=order.customer_full_name,
            shipping_address=order.shipping_address,
            lines=[
                OrderLineModel(
                    product_id=line.product_id,
                    quantity=line.quantity,
                    unit_price_cents=line.unit_price_cents,
                )
                for line in order.lines
            ],
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _order_from_model(model)

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        statement = (
            select(OrderModel)
            .options(selectinload(OrderModel.lines))
            .where(OrderModel.id == order_id)
        )
        model = self._session.scalars(statement).first()
        if model is None:
            raise NotFoundError(f"Order {order_id} was not found.")
        model.status = status.value
        self._session.flush()
        return _order_from_model(model)


class SqlAlchemyAuditEventRepository:
    """Audit-event repository backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: AuditEvent) -> AuditEvent:
        model = AuditEventModel(
            actor_user_id=event.actor_user_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            outcome=event.outcome.value,
            detail=event.detail,
            created_at=event.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return _audit_event_from_model(model)

    def list_recent(self, *, limit: int = 100) -> list[AuditEvent]:
        statement = (
            select(AuditEventModel)
            .order_by(AuditEventModel.id.desc())
            .limit(max(1, min(limit, 500)))
        )
        return [_audit_event_from_model(model) for model in self._session.scalars(statement).all()]


class SqlAlchemyThemeRepository:
    """Store-theme repository backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_store(self, store_id: int) -> StoreTheme | None:
        statement = select(StoreThemeModel).where(StoreThemeModel.store_id == store_id)
        model = self._session.scalars(statement).first()
        return _store_theme_from_model(model) if model is not None else None

    def save(self, theme: StoreTheme) -> StoreTheme:
        statement = select(StoreThemeModel).where(StoreThemeModel.store_id == theme.store_id)
        model = self._session.scalars(statement).first()
        if model is None:
            model = StoreThemeModel(
                store_id=theme.store_id,
                artifact_bytes=theme.artifact_bytes,
                content_type=theme.content_type,
            )
            self._session.add(model)
        else:
            model.artifact_bytes = theme.artifact_bytes
            model.content_type = theme.content_type
        self._session.flush()
        return _store_theme_from_model(model)


class SqlAlchemyReceiptRepository:
    """Order-receipt repository backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_order(self, order_id: int) -> OrderReceipt | None:
        statement = select(OrderReceiptModel).where(OrderReceiptModel.order_id == order_id)
        model = self._session.scalars(statement).first()
        return _order_receipt_from_model(model) if model is not None else None

    def save(self, receipt: OrderReceipt) -> OrderReceipt:
        statement = select(OrderReceiptModel).where(OrderReceiptModel.order_id == receipt.order_id)
        model = self._session.scalars(statement).first()
        if model is None:
            model = OrderReceiptModel(
                order_id=receipt.order_id,
                payload_blob=receipt.payload_blob,
            )
            self._session.add(model)
        else:
            model.payload_blob = receipt.payload_blob
        self._session.flush()
        return _order_receipt_from_model(model)
