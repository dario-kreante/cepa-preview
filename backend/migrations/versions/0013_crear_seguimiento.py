"""crear seguimiento y plazo_programa

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plazo_programa",
        sa.Column("programa", sa.String(length=80), primary_key=True),
        sa.Column("dias_plazo_informe", sa.Integer(), nullable=False),
    )
    op.create_table(
        "seguimiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_acogida", sa.Date(), nullable=True),
        sa.Column("programa", sa.String(length=80), nullable=True),
        sa.Column("eval_medica_estado", sa.String(length=20), nullable=True),
        sa.Column("eval_medica_medico", sa.String(length=120), nullable=True),
        sa.Column("eval_medica_fecha", sa.Date(), nullable=True),
        sa.Column("eval_psico_estado", sa.String(length=20), nullable=True),
        sa.Column("eval_psico_psicologo", sa.String(length=120), nullable=True),
        sa.Column("eval_psico_fecha", sa.Date(), nullable=True),
        sa.Column("obstaculizacion", sa.Boolean(), nullable=False),
        sa.Column("plazo_informe", sa.Integer(), nullable=True),
        sa.Column("fecha_envio_informe", sa.Date(), nullable=True),
        sa.Column("reca_ep_ec", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingreso_id"], ["ingreso.id"], name="fk_seguimiento_ingreso"),
    )
    op.create_unique_constraint("uq_seguimiento_ingreso", "seguimiento", ["ingreso_id"])


def downgrade() -> None:
    op.drop_constraint("uq_seguimiento_ingreso", "seguimiento", type_="unique")
    op.drop_table("seguimiento")
    op.drop_table("plazo_programa")
