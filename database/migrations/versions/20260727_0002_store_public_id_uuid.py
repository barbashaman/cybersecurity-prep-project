"""Add UUIDv4 public identifiers to stores.

Revision ID: 20260727_0002
Revises: 20260726_0001
Create Date: 2026-07-27 10:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0002"
down_revision: str | None = "20260726_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("public_id", sa.String(length=36), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM stores")).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE stores SET public_id = :public_id WHERE id = :store_id"),
            {"public_id": str(uuid.uuid4()), "store_id": row.id},
        )
    op.alter_column("stores", "public_id", nullable=False)
    op.create_unique_constraint("uq_stores_public_id", "stores", ["public_id"])


def downgrade() -> None:
    op.drop_constraint("uq_stores_public_id", "stores", type_="unique")
    op.drop_column("stores", "public_id")
