"""agendamiento tablas: disponibilidad_prof, propuesta_agenda, cita_propuesta

Revision ID: 0801
Revises: 0071
Create Date: 2026-06-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0801"
down_revision = "0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "disponibilidad_prof",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("profesional_id", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("cupo_diario", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_disp_prof_profesional", "disponibilidad_prof", ["profesional_id"])

    op.create_table(
        "propuesta_agenda",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("profesional_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False, server_default="borrador"),
        sa.Column("generado_por", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prop_agenda_profesional", "propuesta_agenda", ["profesional_id"])

    op.create_table(
        "cita_propuesta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("propuesta_id", sa.Integer(), nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.Column("fecha_candidata", sa.Date(), nullable=False),
        sa.Column("prioridad", sa.String(25), nullable=False),
        sa.Column("razon", sa.String(120), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False, server_default="propuesta"),
        sa.Column("excluida_por", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cita_prop_propuesta", "cita_propuesta", ["propuesta_id"])
    op.create_index("ix_cita_prop_paciente", "cita_propuesta", ["paciente_id"])


def downgrade() -> None:
    op.drop_index("ix_cita_prop_paciente", table_name="cita_propuesta")
    op.drop_index("ix_cita_prop_propuesta", table_name="cita_propuesta")
    op.drop_table("cita_propuesta")
    op.drop_index("ix_prop_agenda_profesional", table_name="propuesta_agenda")
    op.drop_table("propuesta_agenda")
    op.drop_index("ix_disp_prof_profesional", table_name="disponibilidad_prof")
    op.drop_table("disponibilidad_prof")
