"""crear folio_seq

Revision ID: 0012
Revises: 0011b
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "folio_seq",
        sa.Column("anio", sa.Integer(), primary_key=True),
        sa.Column("ultimo", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("folio_seq")
