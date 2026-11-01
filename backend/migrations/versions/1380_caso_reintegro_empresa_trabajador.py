"""caso_reintegro: razón social de la empresa y tipo de trabajador; sexo y edad opcionales

QA UTalca 22-10 (QA-008): el alta de un caso de reintegro ya no pide edad ni sexo
(son datos del paciente y los reportes los leen de ``paciente``), y en cambio pide la
razón social de la empresa y si el trabajador es dependiente o independiente.

- ``sexo`` y ``edad`` pasan a nullable. El servicio los sigue copiando desde el paciente
  del ingreso cuando el alta no los trae, así que los casos nuevos los tienen si el
  paciente los tiene.
- Agrega ``razon_social`` (String(160), nullable): se precarga con ``ingreso.razon_social``.
- Agrega ``tipo_trabajador`` (String(20), nullable): ``dependiente`` / ``independiente``.
  Los casos existentes quedan en NULL. Se guarda como texto (sin enum ni CHECK) para que
  sea portable a Oracle, igual que el resto de listas cerradas del módulo.

El downgrade elimina las dos columnas nuevas (se pierden esos datos) y vuelve a exigir
``sexo`` y ``edad``: falla si hay casos sin esos datos; hay que completarlos antes.

Revision ID: 1380
Revises: 1370
"""
import sqlalchemy as sa
from alembic import op

revision = "1380"
down_revision = "1370"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("caso_reintegro", "sexo", existing_type=sa.String(10), nullable=True)
    op.alter_column("caso_reintegro", "edad", existing_type=sa.BigInteger(), nullable=True)
    op.add_column(
        "caso_reintegro", sa.Column("razon_social", sa.String(length=160), nullable=True)
    )
    op.add_column(
        "caso_reintegro", sa.Column("tipo_trabajador", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("caso_reintegro", "tipo_trabajador")
    op.drop_column("caso_reintegro", "razon_social")
    op.alter_column("caso_reintegro", "edad", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("caso_reintegro", "sexo", existing_type=sa.String(10), nullable=False)
