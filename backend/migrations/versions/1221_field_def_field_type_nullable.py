"""field_def.field_type nullable (Oracle trata '' como NULL — D15)

Revision ID: 1221
Revises: 1220
Create Date: 2026-06-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "1221"
down_revision = "1220"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "field_def",
        "field_type",
        existing_type=sa.String(20),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "field_def",
        "field_type",
        existing_type=sa.String(20),
        nullable=False,
    )
