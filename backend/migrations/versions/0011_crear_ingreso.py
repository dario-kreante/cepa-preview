"""crear ingreso

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingreso",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("paciente_id", sa.BigInteger(), nullable=False),
        sa.Column("folio", sa.String(length=30), nullable=False),
        sa.Column("folio_manual", sa.Boolean(), nullable=False),
        sa.Column("numero_siniestro", sa.String(length=40), nullable=True),
        sa.Column("fecha_ingreso", sa.Date(), nullable=False),
        sa.Column("fecha_diep_diat", sa.Date(), nullable=True),
        sa.Column("tipo_derivacion", sa.String(length=40), nullable=False),
        sa.Column("tipo_ingreso", sa.String(length=40), nullable=False),
        sa.Column("modelo_tratamiento", sa.String(length=80), nullable=False),
        sa.Column("diagnostico", sa.String(length=200), nullable=False),
        sa.Column("razon_social", sa.String(length=160), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("tipo_alta", sa.String(length=20), nullable=True),
        sa.Column("fecha_alta", sa.Date(), nullable=True),
        sa.Column("flag_revision", sa.Boolean(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("tratamiento_iniciado", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paciente_id"], ["paciente.id"], name="fk_ingreso_paciente"),
    )
    op.create_unique_constraint("uq_ingreso_folio", "ingreso", ["folio"])
    op.create_index("ix_ingreso_folio", "ingreso", ["folio"])
    op.create_index("ix_ingreso_paciente_id", "ingreso", ["paciente_id"])
    op.create_index("ix_ingreso_num_siniestro", "ingreso", ["numero_siniestro"])


def downgrade() -> None:
    op.drop_index("ix_ingreso_num_siniestro", table_name="ingreso")
    op.drop_index("ix_ingreso_paciente_id", table_name="ingreso")
    op.drop_index("ix_ingreso_folio", table_name="ingreso")
    op.drop_constraint("uq_ingreso_folio", "ingreso", type_="unique")
    op.drop_table("ingreso")
