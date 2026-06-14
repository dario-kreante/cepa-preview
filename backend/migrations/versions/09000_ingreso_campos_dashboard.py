"""Añadir campos de dimensión para dashboard a la tabla ingreso y crear tabla cita.

Revision ID: 09000
Revises: 0801
Create Date: 2026-06-11 00:00:00.000000

Deviación declarada EPIC-09 D1: el modelo Ingreso carecía de los campos de
dimensión (programa, profesional_id, tipo_convenio, sexo, region, comuna,
tramo_etario, especialidad, tipo_atencion) requeridos por los filtros D5 del
dashboard. Se agregan como nullable para no romper filas existentes.
sexo/region/comuna ya existen en Paciente pero no en Ingreso; se agregan
directamente en ingreso para simplificar los filtros de reporting.

Deviación declarada EPIC-09 D2: no existe modelo Cita previo a esta épica
(solo CitaPropuesta en agendamiento). Se crea la tabla `cita` para los
reportes operativos.

Deviación declarada EPIC-09 D3: PlanTratamiento no existía. Se crea la tabla
`plan_tratamiento` para métricas de adherencia/avance (CEPA-095).

Deviación declarada EPIC-09 D4: ODA carece de fecha_registro. Se añade como
Date nullable.
"""
from alembic import op
import sqlalchemy as sa

revision = "09000"
down_revision = "0801"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Campos de dimensión en ingreso ────────────────────────────────────────
    with op.batch_alter_table("ingreso") as batch_op:
        batch_op.add_column(sa.Column("programa", sa.String(40), nullable=True))
        batch_op.add_column(sa.Column("profesional_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("tipo_convenio", sa.String(40), nullable=True))
        batch_op.add_column(sa.Column("sexo", sa.String(10), nullable=True))
        batch_op.add_column(sa.Column("region", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("comuna", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("tramo_etario", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("especialidad", sa.String(60), nullable=True))
        batch_op.add_column(sa.Column("tipo_atencion", sa.String(40), nullable=True))

    # ── Tabla cita (para reportes operativos EPIC-09) ─────────────────────────
    op.create_table(
        "cita",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "ingreso_id",
            sa.BigInteger(),
            sa.ForeignKey("ingreso.id"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_cita_ingreso_id", "cita", ["ingreso_id"])
    op.create_index("ix_cita_fecha", "cita", ["fecha"])

    # ── fecha_registro en ODA ─────────────────────────────────────────────────
    with op.batch_alter_table("oda") as batch_op:
        batch_op.add_column(sa.Column("fecha_registro", sa.Date(), nullable=True))

    # ── Tabla plan_tratamiento (para adherencia/avance EPIC-09 CEPA-095) ──────
    op.create_table(
        "plan_tratamiento",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "ingreso_id",
            sa.BigInteger(),
            sa.ForeignKey("ingreso.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("sesiones_plan", sa.Integer(), nullable=True),
        sa.Column("aumentos_isl", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("plan_tratamiento")

    with op.batch_alter_table("oda") as batch_op:
        batch_op.drop_column("fecha_registro")

    op.drop_index("ix_cita_fecha", table_name="cita")
    op.drop_index("ix_cita_ingreso_id", table_name="cita")
    op.drop_table("cita")

    with op.batch_alter_table("ingreso") as batch_op:
        batch_op.drop_column("tipo_atencion")
        batch_op.drop_column("especialidad")
        batch_op.drop_column("tramo_etario")
        batch_op.drop_column("comuna")
        batch_op.drop_column("region")
        batch_op.drop_column("sexo")
        batch_op.drop_column("tipo_convenio")
        batch_op.drop_column("profesional_id")
        batch_op.drop_column("programa")
