"""control_medico: notas de SALUTEM y addendum (QA-008, 24-11-2026)

En SALUTEM el addendum no es un campo de la ficha: el equipo lo registra como una entrada de
la lista ``notas`` de la atención (texto HTML, fecha de creación y profesional), que puede
agregarse días después de atender. SIGE ignoraba las notas y la tester no veía el addendum.

- ``control_medico.notas_salutem`` (Text, nullable): todas las notas de la atención ya
  limpias (HTML → texto plano), serializadas como JSON: ``[{"fecha", "profesional",
  "texto"}]``. CLOB en Oracle; el sync la compara en Python, nunca en SQL. Cuáles son
  addendum se decide al leer (app.domain.addendum), no se guarda.

Los controles existentes la reciben al correr `salutem_sync vincular --todo`. El downgrade
elimina la columna; se recupera volviendo a vincular.

Revision ID: 1570
Revises: 1530
"""
import sqlalchemy as sa
from alembic import op

revision = "1570"
down_revision = "1530"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("control_medico", sa.Column("notas_salutem", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("control_medico", "notas_salutem")
