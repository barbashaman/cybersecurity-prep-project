"""iter-03 store_themes and order_receipts tables (A08 vehicle).

Revision ID: 20260726_0003
Revises: 20260726_0002
Create Date: 2026-07-26 19:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260726_0003"
down_revision: str | None = "20260726_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "store_themes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("artifact_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", name="uq_store_themes_store_id"),
    )
    op.create_table(
        "order_receipts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("payload_blob", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_order_receipts_order_id"),
    )


def downgrade() -> None:
    op.drop_table("order_receipts")
    op.drop_table("store_themes")
