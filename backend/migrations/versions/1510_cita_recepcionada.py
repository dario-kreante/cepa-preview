"""cita: estado «recepcionada» para las citas recepcionadas en SALUTEM (QA-002, 23-11-2026)

Hasta ahora una cita RECEPCIONADO (estado 8) de SALUTEM se guardaba como «agendada». El
CEPA quiere verlas aparte para saber qué atenciones faltan por evolucionar. El sync ya
las escribe como «recepcionada»; esta migración corrige las que ya estaban guardadas.

El downgrade las devuelve a «agendada».

Revision ID: 1510
Revises: 1500
"""
from alembic import op

revision = "1510"
down_revision = "1500"
branch_labels = None
depends_on = None

RECEPCIONADO = 8


def upgrade() -> None:
    op.execute(
        "UPDATE cita SET estado = 'recepcionada' "
        "WHERE estado = 'agendada' AND salutem_cita_id IN "
        f"(SELECT cita_id FROM salutem_cita WHERE estado_id = {RECEPCIONADO})"
    )


def downgrade() -> None:
    op.execute("UPDATE cita SET estado = 'agendada' WHERE estado = 'recepcionada'")
