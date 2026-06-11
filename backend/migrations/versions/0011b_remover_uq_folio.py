"""remover unique constraint de folio (reingresos permitidos)

Revision ID: 0011b
Revises: 0011
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op

revision = "0011b"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remover unique constraint pero mantener el índice para búsquedas rápidas
    op.drop_constraint("uq_ingreso_folio", "ingreso", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("uq_ingreso_folio", "ingreso", ["folio"])
