"""crear esquema_indicacion

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "esquema_indicacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("registro_id", sa.BigInteger(), nullable=False),
        sa.Column("medicamento", sa.String(length=200), nullable=False),
        sa.Column("dosis", sa.String(length=80), nullable=False),
        sa.Column("frecuencia", sa.String(length=40), nullable=False),
        sa.Column("extra_sistema", sa.Boolean(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registro_id"], ["reg_farmacologico.id"], name="fk_esq_ind_registro"
        ),
    )
    op.create_index("ix_esq_ind_registro_id", "esquema_indicacion", ["registro_id"])


def downgrade() -> None:
    op.drop_index("ix_esq_ind_registro_id", table_name="esquema_indicacion")
    op.drop_table("esquema_indicacion")
