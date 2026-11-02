"""control_medico: campos corregidos a mano en SIGE

Reunión de revisión 29-10-2026 (D4): cuando SALUTEM no trae los días de licencia o el
reposo, o un adendum del médico los corrige, el CEPA los corrige en SIGE. Hasta ahora el
sync de SALUTEM volvía a escribir esos campos en el siguiente ciclo.

- Agrega ``campos_editados`` (String(500), nullable): nombres de columna corregidos a mano,
  separados por coma. El sync los omite al actualizar el control. Los controles existentes
  quedan en NULL (nada corregido).

El downgrade elimina la columna: el sync vuelve a escribir todos los campos.

Revision ID: 1390
Revises: 1380
"""
import sqlalchemy as sa
from alembic import op

revision = "1390"
down_revision = "1380"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "control_medico", sa.Column("campos_editados", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("control_medico", "campos_editados")
