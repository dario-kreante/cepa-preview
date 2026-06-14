"""crear control_medico (CEPA-060)

Revision ID: 0060
Revises: 0041
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0060"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "control_medico",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_control", sa.Date(), nullable=False),
        sa.Column("semana_control", sa.Integer(), nullable=False),
        sa.Column("medico_tratante", sa.String(length=160), nullable=False),
        sa.Column("region_derivacion", sa.String(length=80), nullable=False),
        sa.Column("proximo_control", sa.Date(), nullable=True),
        sa.Column("proximo_agendado", sa.Boolean(), nullable=False),
        sa.Column("tiene_licencia", sa.Boolean(), nullable=False),
        sa.Column("resumen_termino_lm", sa.String(length=500), nullable=True),
        sa.Column("total_dias_lm", sa.Integer(), nullable=True),
        sa.Column("tipo_licencia", sa.String(length=20), nullable=True),
        sa.Column("tipo_reposo", sa.String(length=10), nullable=True),
        sa.Column("gaf", sa.Integer(), nullable=True),
        sa.Column("estado_reca", sa.String(length=20), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingreso_id"], ["ingreso.id"], name="fk_ctrl_med_ingreso"
        ),
    )
    op.create_index("ix_ctrl_med_ingreso_id", "control_medico", ["ingreso_id"])
    op.create_index("ix_ctrl_med_fecha", "control_medico", ["fecha_control"])


def downgrade() -> None:
    op.drop_index("ix_ctrl_med_fecha", table_name="control_medico")
    op.drop_index("ix_ctrl_med_ingreso_id", table_name="control_medico")
    op.drop_table("control_medico")
