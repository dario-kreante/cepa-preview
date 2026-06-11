"""crear alerta

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("receta_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("mensaje", sa.String(length=300), nullable=False),
        sa.Column("leida", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["receta_id"], ["receta.id"], name="fk_alerta_receta"),
    )
    op.create_index("ix_alerta_receta_id", "alerta", ["receta_id"])
    op.create_index("ix_alerta_leida", "alerta", ["leida"])


def downgrade() -> None:
    op.drop_index("ix_alerta_leida", table_name="alerta")
    op.drop_index("ix_alerta_receta_id", table_name="alerta")
    op.drop_table("alerta")
