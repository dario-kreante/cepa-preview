"""ingreso: cierre del caso con motivo, fecha y usuario (QA-011, 16-11-2026)

- ``motivo_cierre``: lista propia (reca_ec, alta_medica, alta_administrativa, abandono,
  desiste_proceso, cambio_prestador), separada de ``tipo_alta``.
- ``fecha_cierre`` y ``cierre_usuario``: cuándo y quién cerró el caso.

Los tres quedan en NULL en los casos ya cerrados antes de este cambio y se limpian al reabrir.

Revision ID: 1480
Revises: 1470
"""
import sqlalchemy as sa
from alembic import op

revision = "1480"
down_revision = "1470"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingreso", sa.Column("motivo_cierre", sa.String(30), nullable=True))
    op.add_column("ingreso", sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingreso", sa.Column("cierre_usuario", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("ingreso", "cierre_usuario")
    op.drop_column("ingreso", "fecha_cierre")
    op.drop_column("ingreso", "motivo_cierre")
