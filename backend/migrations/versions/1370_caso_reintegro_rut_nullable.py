"""caso_reintegro.rut nullable: el paciente puede venir de SALUTEM sin RUT

Un caso de reintegro se abre sobre un ingreso existente. Si el paciente no tiene RUT
(los borradores que crea el sync de SALUTEM pueden no traerlo), el caso no se podía
crear. Ahora el RUT se toma del paciente cuando no se indica y puede quedar vacío.

El downgrade falla si hay casos sin RUT: hay que completarlos antes.

Revision ID: 1370
Revises: 1365
"""
import sqlalchemy as sa
from alembic import op

revision = "1370"
down_revision = "1365"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("caso_reintegro", "rut", existing_type=sa.String(12), nullable=True)


def downgrade() -> None:
    op.alter_column("caso_reintegro", "rut", existing_type=sa.String(12), nullable=False)
