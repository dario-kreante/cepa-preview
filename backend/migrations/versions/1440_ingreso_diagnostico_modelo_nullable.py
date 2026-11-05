"""ingreso: diagnóstico y modelo de tratamiento opcionales

Registro de pruebas QA del 29-10-2026 (QA-004, Alejandra Herrera): ambos datos se obtienen
después de algunos controles médicos, así que no se pueden exigir al crear el ingreso.
Los ingresos existentes conservan sus valores.

El downgrade falla si ya hay ingresos sin estos datos: hay que completarlos antes.

Revision ID: 1440
Revises: 1430
"""
import sqlalchemy as sa
from alembic import op

revision = "1440"
down_revision = "1430"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("ingreso", "modelo_tratamiento", existing_type=sa.String(80), nullable=True)
    op.alter_column("ingreso", "diagnostico", existing_type=sa.String(200), nullable=True)


def downgrade() -> None:
    op.alter_column("ingreso", "diagnostico", existing_type=sa.String(200), nullable=False)
    op.alter_column("ingreso", "modelo_tratamiento", existing_type=sa.String(80), nullable=False)
