"""salutem_persona: fecha de creación en SALUTEM

El paciente borrador se crea desde que la persona existe en SALUTEM, aunque todavía no
tenga citas ni atenciones (05-11-2026). La fecha viene de `GET /personas` por rango; la
ficha demográfica no la trae, así que puede quedar vacía en personas ya copiadas.

Revision ID: 1460
Revises: 1450
"""
import sqlalchemy as sa
from alembic import op

revision = "1460"
down_revision = "1450"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("salutem_persona", sa.Column("fecha_creacion", sa.DateTime(), nullable=True))
    op.create_index("ix_salutem_persona_creacion", "salutem_persona", ["fecha_creacion"])


def downgrade() -> None:
    op.drop_index("ix_salutem_persona_creacion", table_name="salutem_persona")
    op.drop_column("salutem_persona", "fecha_creacion")
