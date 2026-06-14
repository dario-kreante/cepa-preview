"""crear reca (CEPA-041)

Revision ID: 0041
Revises: 0040
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reca",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("caso_reintegro_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_reca", sa.Date(), nullable=False),
        sa.Column("tipo_reca", sa.String(length=10), nullable=False),
        sa.Column("numero_reca", sa.String(length=40), nullable=False),
        sa.Column("riesgos_calificados", sa.Text(), nullable=True),
        sa.Column("razon_social", sa.String(length=160), nullable=False),
        sa.Column("solicita_medidas", sa.Boolean(), nullable=False),
        sa.Column("detalle_medidas", sa.Text(), nullable=True),
        sa.Column("fecha_medidas", sa.Date(), nullable=True),
        sa.Column("verifica_medidas", sa.Boolean(), nullable=False),
        sa.Column("detalle_verificacion", sa.Text(), nullable=True),
        sa.Column("fecha_verificacion", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["caso_reintegro_id"],
            ["caso_reintegro.id"],
            name="fk_reca_caso_reintegro",
        ),
        sa.UniqueConstraint(
            "numero_reca", "caso_reintegro_id", name="uq_reca_numero_caso"
        ),
    )
    op.create_index("ix_reca_caso_reintegro_id", "reca", ["caso_reintegro_id"])


def downgrade() -> None:
    op.drop_index("ix_reca_caso_reintegro_id", table_name="reca")
    op.drop_table("reca")
