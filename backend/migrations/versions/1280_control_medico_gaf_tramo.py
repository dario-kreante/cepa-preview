"""control_medico: gaf_tramo, el GAF por tramo que registra SALUTEM ("51-60")

Revision ID: 1280
Revises: 1270
"""

import sqlalchemy as sa
from alembic import op

revision = "1280"
down_revision = "1270"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("control_medico", sa.Column("gaf_tramo", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("control_medico", "gaf_tramo")
