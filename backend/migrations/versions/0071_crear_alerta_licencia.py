"""crear alerta_licencia

Revision ID: 0071
Revises: 0070
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerta_licencia",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("licencia_id", sa.BigInteger(), nullable=False),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_termino_lm", sa.Date(), nullable=False),
        sa.Column("dias_habiles_restantes", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["licencia_id"], ["licencia_medica.id"], name="fk_alerta_licencia"
        ),
    )
    op.create_index("ix_alerta_licencia_id", "alerta_licencia", ["licencia_id"])
    op.create_index("ix_alerta_ingreso_id", "alerta_licencia", ["ingreso_id"])


def downgrade() -> None:
    op.drop_index("ix_alerta_ingreso_id", table_name="alerta_licencia")
    op.drop_index("ix_alerta_licencia_id", table_name="alerta_licencia")
    op.drop_table("alerta_licencia")
