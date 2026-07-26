"""iter-06 order notes column (A05 injection vehicle).

Revision ID: 20260726_0006
Revises: 20260726_0005
Create Date: 2026-07-26 18:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260726_0006"
down_revision: str | None = "20260726_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
    )
    # PLAN FIX (A05): no schema change required for search — use bound parameters
    # in the repository instead of string-concatenated SQL.


def downgrade() -> None:
    op.drop_column("orders", "notes")
