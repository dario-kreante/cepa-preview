"""gestion_citacion: bitácora de intentos de contacto con pacientes por citar

- Crea ``gestion_citacion`` (paciente, profesional, resultado, nota, usuario, fecha) con FKs a
  ``paciente`` y ``profesional`` e índice en ``paciente_id``. Sin datos que sembrar.

Se numeró 1355 (antes 1350) para ir después de ``1350_profesional_salutem``: las dos ramas
crearon una 1350 desde la 1340 y en main quedaban dos cabezas.

Revision ID: 1355
Revises: 1350
"""

import sqlalchemy as sa
from alembic import op

revision = "1355"
down_revision = "1350"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gestion_citacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("paciente_id", sa.BigInteger(), sa.ForeignKey("paciente.id"), nullable=False),
        sa.Column("profesional_id", sa.BigInteger(), sa.ForeignKey("profesional.id"), nullable=False),
        sa.Column("resultado", sa.String(length=25), nullable=False),
        sa.Column("nota", sa.String(length=300), nullable=True),
        sa.Column("usuario", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_gestion_citacion_paciente_id", "gestion_citacion", ["paciente_id"])


def downgrade() -> None:
    op.drop_index("ix_gestion_citacion_paciente_id", table_name="gestion_citacion")
    op.drop_table("gestion_citacion")
