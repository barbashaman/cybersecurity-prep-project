"""SQLAlchemy 2.0 ORM models for the Phase 1b baseline schema."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class UserModel(Base):
    """Persisted user row."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    store_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True
    )


class StoreModel(Base):
    """Persisted store row."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # use_alter breaks the users <-> stores circular foreign-key dependency.
    owner_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_stores_owner_user_id",
        ),
        nullable=True,
    )

    products: Mapped[list[ProductModel]] = relationship(back_populates="store")
    orders: Mapped[list[OrderModel]] = relationship(back_populates="store")


class ProductModel(Base):
    """Persisted product row."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    store: Mapped[StoreModel] = relationship(back_populates="products")


class OrderModel(Base):
    """Persisted order row (includes customer PII columns)."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    customer_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    customer_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)

    store: Mapped[StoreModel] = relationship(back_populates="orders")
    lines: Mapped[list[OrderLineModel]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderLineModel(Base):
    """Persisted order-line row."""

    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[OrderModel] = relationship(back_populates="lines")


class AuditEventModel(Base):
    """Persisted admin audit-trail row (iter-02)."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StoreThemeModel(Base):
    """Persisted store theme artifact row (iter-03)."""

    __tablename__ = "store_themes"
    __table_args__ = (UniqueConstraint("store_id", name="uq_store_themes_store_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    artifact_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)


class OrderReceiptModel(Base):
    """Persisted order receipt blob row (iter-03)."""

    __tablename__ = "order_receipts"
    __table_args__ = (UniqueConstraint("order_id", name="uq_order_receipts_order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    payload_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class PasswordResetTokenModel(Base):
    """Persisted password-reset token row (iter-04)."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (UniqueConstraint("token", name="uq_password_reset_tokens_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False)
