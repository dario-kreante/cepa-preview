"""crear receta

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("registro_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_revision", sa.Date(), nullable=False),
        sa.Column("fecha_envio", sa.Date(), nullable=True),
        sa.Column("marca_medicamento", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registro_id"], ["reg_farmacologico.id"], name="fk_receta_registro"
        ),
    )
    op.create_index("ix_receta_registro_id", "receta", ["registro_id"])
    op.create_index("ix_receta_fecha_revision", "receta", ["fecha_revision"])


def downgrade() -> None:
    op.drop_index("ix_receta_fecha_revision", table_name="receta")
    op.drop_index("ix_receta_registro_id", table_name="receta")
    op.drop_table("receta")
