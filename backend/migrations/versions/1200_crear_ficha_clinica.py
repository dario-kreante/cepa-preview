"""crear ficha_clinica

Revision ID: 1200
Revises: 11002
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "1200"
down_revision = "11002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ficha_clinica",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("folio", sa.String(length=30), nullable=False),
        sa.Column("origen", sa.String(length=40), nullable=False),
        sa.Column("contenido", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_ficha_clinica_ingreso"
        ),
    )
    op.create_index("ix_ficha_clinica_folio", "ficha_clinica", ["folio"])
    op.create_index("ix_ficha_clinica_ingreso_id", "ficha_clinica", ["ingreso_id"])


def downgrade() -> None:
    op.drop_index("ix_ficha_clinica_ingreso_id", table_name="ficha_clinica")
    op.drop_index("ix_ficha_clinica_folio", table_name="ficha_clinica")
    op.drop_table("ficha_clinica")
