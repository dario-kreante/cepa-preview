"""control_medico: evaluación clínica de la ficha del CEPA

Tiempo estimado de tratamiento, proyección de reintegro laboral y factores de riesgo
acogidos. Los llena el sync desde SALUTEM o se editan en SIGE.

Revision ID: 1310
Revises: 1300
"""

import sqlalchemy as sa
from alembic import op

revision = "1310"
down_revision = "1300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "control_medico",
        sa.Column("tiempo_estimado_tratamiento", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "control_medico", sa.Column("proyeccion_reintegro", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "control_medico", sa.Column("factores_riesgo", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("control_medico", "factores_riesgo")
    op.drop_column("control_medico", "proyeccion_reintegro")
    op.drop_column("control_medico", "tiempo_estimado_tratamiento")
