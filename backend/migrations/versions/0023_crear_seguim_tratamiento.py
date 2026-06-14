"""crear seguim_tratamiento

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seguim_tratamiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("registro_id", sa.BigInteger(), nullable=False),
        sa.Column("disminucion_farmacos", sa.Boolean(), nullable=False),
        sa.Column("plan_disminucion", sa.Text(), nullable=True),
        sa.Column("cambio_esquema", sa.Boolean(), nullable=False),
        sa.Column("detalle_cambio", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registro_id"], ["reg_farmacologico.id"], name="fk_seguim_registro"
        ),
    )
    op.create_index("ix_seguim_registro_id", "seguim_tratamiento", ["registro_id"])


def downgrade() -> None:
    op.drop_index("ix_seguim_registro_id", table_name="seguim_tratamiento")
    op.drop_table("seguim_tratamiento")
