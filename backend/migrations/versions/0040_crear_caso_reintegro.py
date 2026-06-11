"""crear caso_reintegro (CEPA-040)

Revision ID: 0040
Revises: 0030
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0040"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caso_reintegro",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("rut", sa.String(length=12), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("tipo_derivacion", sa.String(length=40), nullable=False),
        sa.Column("fecha_caso", sa.Date(), nullable=False),
        sa.Column("sexo", sa.String(length=10), nullable=False),
        sa.Column("edad", sa.BigInteger(), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("comuna", sa.String(length=80), nullable=True),
        sa.Column("rubro_empleador", sa.String(length=160), nullable=True),
        sa.Column("estado_reintegro", sa.String(length=20), nullable=False),
        sa.Column("fecha_reintegro", sa.Date(), nullable=True),
        sa.Column("remitido_isl", sa.Boolean(), nullable=False),
        sa.Column("alta_medica", sa.Boolean(), nullable=False),
        sa.Column("fecha_alta_medica", sa.Date(), nullable=True),
        sa.Column("alta_psicologica", sa.Boolean(), nullable=False),
        sa.Column("fecha_alta_psico", sa.Date(), nullable=True),
        sa.Column("tipo_alta", sa.String(length=20), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_caso_reintegro_ingreso"
        ),
    )
    op.create_index("ix_caso_reintegro_rut", "caso_reintegro", ["rut"])
    op.create_index("ix_caso_reintegro_ingr", "caso_reintegro", ["ingreso_id"])


def downgrade() -> None:
    op.drop_index("ix_caso_reintegro_ingr", table_name="caso_reintegro")
    op.drop_index("ix_caso_reintegro_rut", table_name="caso_reintegro")
    op.drop_table("caso_reintegro")
