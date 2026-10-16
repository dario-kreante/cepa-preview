"""paciente: estado de registro, origen y datos opcionales para borradores

Los pacientes borrador creados desde SALUTEM quedan en `pendiente_folio` sin RUT, sexo,
edad ni región hasta que se complete su registro.

Downgrade: falla si existen borradores con rut/sexo/edad/region nulos; hay que completarlos
o eliminarlos antes de bajar.

Revision ID: 1330
Revises: 1320
"""

import sqlalchemy as sa
from alembic import op

revision = "1330"
down_revision = "1320"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paciente",
        sa.Column("estado_registro", sa.String(length=20), nullable=False, server_default="completo"),
    )
    op.add_column(
        "paciente",
        sa.Column("origen", sa.String(length=10), nullable=False, server_default="SIGE"),
    )
    op.add_column("paciente", sa.Column("motivo_descarte", sa.String(length=300), nullable=True))
    op.add_column("paciente", sa.Column("descartado_por", sa.String(length=80), nullable=True))
    op.add_column("paciente", sa.Column("descartado_en", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_paciente_estado_registro", "paciente", ["estado_registro"])
    op.alter_column("paciente", "rut", existing_type=sa.String(length=12), nullable=True)
    op.alter_column("paciente", "sexo", existing_type=sa.String(length=10), nullable=True)
    op.alter_column("paciente", "edad", existing_type=sa.Integer(), nullable=True)
    op.alter_column("paciente", "region", existing_type=sa.String(length=80), nullable=True)


def downgrade() -> None:
    op.alter_column("paciente", "region", existing_type=sa.String(length=80), nullable=False)
    op.alter_column("paciente", "edad", existing_type=sa.Integer(), nullable=False)
    op.alter_column("paciente", "sexo", existing_type=sa.String(length=10), nullable=False)
    op.alter_column("paciente", "rut", existing_type=sa.String(length=12), nullable=False)
    op.drop_index("ix_paciente_estado_registro", table_name="paciente")
    op.drop_column("paciente", "descartado_en")
    op.drop_column("paciente", "descartado_por")
    op.drop_column("paciente", "motivo_descarte")
    op.drop_column("paciente", "origen")
    op.drop_column("paciente", "estado_registro")
