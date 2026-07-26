"""iter-07 customer phone PII column (A04 cryptographic failures vehicle).

Revision ID: 20260726_0007
Revises: 20260726_0006
Create Date: 2026-07-26 18:40:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260726_0007"
down_revision: str | None = "20260726_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # VULNERABLE (A04): sensitive contact PII column stored as plaintext Text.
    # PLAN FIX (A04): encrypt at rest (AES-GCM / Fernet) with KMS-managed keys;
    # keep ciphertext + nonce columns (or envelope encryption) instead of cleartext.
    op.add_column(
        "orders",
        sa.Column("customer_phone", sa.String(length=64), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("orders", "customer_phone")
