"""crear oda

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oda",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("identificador", sa.String(length=60), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingreso_id"], ["ingreso.id"], name="fk_oda_ingreso"),
    )
    op.create_index("ix_oda_ingreso_id", "oda", ["ingreso_id"])
    op.create_index("ix_oda_fecha_venc", "oda", ["fecha_vencimiento"])


def downgrade() -> None:
    op.drop_index("ix_oda_fecha_venc", table_name="oda")
    op.drop_index("ix_oda_ingreso_id", table_name="oda")
    op.drop_table("oda")
