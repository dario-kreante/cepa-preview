"""crear imed_payload

Revision ID: 1220
Revises: 1200
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "1220"
down_revision = "1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imed_payload",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("folio", sa.String(length=30), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("datos", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_imed_payload_folio", "imed_payload", ["folio"])


def downgrade() -> None:
    op.drop_index("ix_imed_payload_folio", table_name="imed_payload")
    op.drop_table("imed_payload")
