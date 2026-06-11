"""crear paciente

Revision ID: 0010
Revises: 0003
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paciente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("rut", sa.String(length=12), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("sexo", sa.String(length=10), nullable=False),
        sa.Column("edad", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("comuna", sa.String(length=80), nullable=True),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column("correo", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_paciente_rut", "paciente", ["rut"])
    op.create_index("ix_paciente_rut", "paciente", ["rut"])
    op.create_index("ix_paciente_nombre", "paciente", ["nombre"])


def downgrade() -> None:
    op.drop_index("ix_paciente_nombre", table_name="paciente")
    op.drop_index("ix_paciente_rut", table_name="paciente")
    op.drop_constraint("uq_paciente_rut", "paciente", type_="unique")
    op.drop_table("paciente")
