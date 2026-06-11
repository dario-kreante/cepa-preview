"""crear config_ventana_proceso

Revision ID: 09001
Revises: 09000
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "09001"
down_revision = "09000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_ventana_proceso",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("proceso", sa.String(length=40), nullable=False),
        sa.Column("columnas_visibles", sa.JSON(), nullable=False),
        sa.Column("orden_por_defecto", sa.String(length=60), nullable=True),
        sa.Column("creado_por", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_cvp_proceso", "config_ventana_proceso", ["proceso"])


def downgrade() -> None:
    op.drop_index("ix_cvp_proceso", table_name="config_ventana_proceso")
    op.drop_table("config_ventana_proceso")
