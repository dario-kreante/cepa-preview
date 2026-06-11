"""crear licencia_medica

Revision ID: 0070
Revises: 0060
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0070"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "licencia_medica",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("folio_lm", sa.String(length=40), nullable=True),
        sa.Column("tipo_lm", sa.String(length=5), nullable=False),
        sa.Column("tipo_reposo", sa.String(length=15), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_termino", sa.Date(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("inicio_reposo", sa.Date(), nullable=False),
        sa.Column("fin_reposo", sa.Date(), nullable=False),
        sa.Column("cantidad_dias", sa.Integer(), nullable=False),
        sa.Column("indicacion_reposo", sa.String(length=300), nullable=True),
        sa.Column("diagnostico", sa.String(length=200), nullable=False),
        sa.Column("origen", sa.String(length=20), nullable=False),
        sa.Column("envio_isl", sa.String(length=15), nullable=False),
        sa.Column("fecha_envio_isl", sa.Date(), nullable=True),
        sa.Column("eeag_gaf", sa.Integer(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("anulada", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_licencia_ingreso"
        ),
    )
    op.create_index("ix_licencia_ingreso_id", "licencia_medica", ["ingreso_id"])
    op.create_index("ix_licencia_folio_lm", "licencia_medica", ["folio_lm"])


def downgrade() -> None:
    op.drop_index("ix_licencia_folio_lm", table_name="licencia_medica")
    op.drop_index("ix_licencia_ingreso_id", table_name="licencia_medica")
    op.drop_table("licencia_medica")
