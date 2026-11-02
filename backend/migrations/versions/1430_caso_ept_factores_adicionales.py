"""caso_ept: hasta 2 factores de riesgo adicionales (3 en total)

Reunión de revisión 29-10-2026 (D11, Carla Hevia): el área explora hasta 3 factores de
riesgo por caso EPT. ``factor_riesgo`` sigue siendo el principal (obligatorio); se agrega
``factores_adicionales`` (String(90), nullable): hasta 2 slugs más separados por coma
(cada slug ≤ 40). Los casos existentes quedan en NULL (solo el principal).

El downgrade elimina la columna: se pierden los factores adicionales.

Revision ID: 1430
Revises: 1420
"""
import sqlalchemy as sa
from alembic import op

revision = "1430"
down_revision = "1420"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "caso_ept", sa.Column("factores_adicionales", sa.String(length=90), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("caso_ept", "factores_adicionales")
