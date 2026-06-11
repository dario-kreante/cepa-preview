"""crear reg_farmacologico

Revision ID: 0020
Revises: 0015
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reg_farmacologico",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("medico_tratante", sa.String(length=160), nullable=False),
        sa.Column("estado_farmacologico", sa.String(length=40), nullable=False),
        sa.Column("antecedentes_previos", sa.Text(), nullable=True),
        sa.Column("tratamiento_previo", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_reg_farm_ingreso"
        ),
    )
    op.create_unique_constraint("uq_reg_farm_ingreso_id", "reg_farmacologico", ["ingreso_id"])
    op.create_index("ix_reg_farm_ingreso_id", "reg_farmacologico", ["ingreso_id"])


def downgrade() -> None:
    op.drop_index("ix_reg_farm_ingreso_id", table_name="reg_farmacologico")
    op.drop_constraint("uq_reg_farm_ingreso_id", "reg_farmacologico", type_="unique")
    op.drop_table("reg_farmacologico")
