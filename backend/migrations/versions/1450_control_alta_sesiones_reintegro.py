"""control_medico: alta, sesiones y observaciones de reintegro desde SALUTEM

Excel «Prestaciones y campos SALUTEM-CEPA» (22-10-2026): campos que el CEPA asignó a los
módulos Controles y Reintegro y que el sync no leía. Son de solo lectura y se guardan tal
como vienen: en SALUTEM la fecha de alta y las sesiones son texto libre. Los controles
existentes los reciben al correr `salutem_sync vincular --todo`.

El downgrade elimina las columnas; se recuperan volviendo a vincular.

Revision ID: 1450
Revises: 1440
"""
import sqlalchemy as sa
from alembic import op

revision = "1450"
down_revision = "1440"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("control_medico", sa.Column("tipo_alta", sa.String(length=80), nullable=True))
    op.add_column("control_medico", sa.Column("fecha_alta", sa.String(length=80), nullable=True))
    op.add_column("control_medico", sa.Column("numero_sesion_actual", sa.String(length=20), nullable=True))
    op.add_column(
        "control_medico", sa.Column("numero_sesiones_tratamiento", sa.String(length=20), nullable=True)
    )
    op.add_column("control_medico", sa.Column("observaciones_reintegro", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("control_medico", "observaciones_reintegro")
    op.drop_column("control_medico", "numero_sesiones_tratamiento")
    op.drop_column("control_medico", "numero_sesion_actual")
    op.drop_column("control_medico", "fecha_alta")
    op.drop_column("control_medico", "tipo_alta")
