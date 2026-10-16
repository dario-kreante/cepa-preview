"""profesional: catálogo de profesionales para el agendamiento

- Crea ``profesional`` (nombre único, especialidad opcional, origen SALUTEM/SIGE, activo).
- La siembra con los médicos tratantes distintos de los controles que vinieron de SALUTEM,
  sin el marcador "Sin profesional informado". INSERT ... SELECT DISTINCT armado con Core para
  que ``true()`` se traduzca a TRUE (Postgres) o 1 (Oracle 19c); la identidad genera el id.
- No toca ``disponibilidad_prof`` ni ``propuesta_agenda``: sus ``profesional_id`` previos eran
  números sueltos de prueba y siguen siendo enteros sin FK.

Revision ID: 1340
Revises: 1330
"""

import sqlalchemy as sa
from alembic import op

revision = "1340"
down_revision = "1330"
branch_labels = None
depends_on = None

SIN_PROFESIONAL = "Sin profesional informado"


def _sembrar() -> None:
    control = sa.table(
        "control_medico", sa.column("medico_tratante", sa.String), sa.column("origen", sa.String)
    )
    profesional = sa.table(
        "profesional",
        sa.column("nombre", sa.String),
        sa.column("origen", sa.String),
        sa.column("activo", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    nombres = (
        sa.select(
            control.c.medico_tratante,
            sa.literal("SALUTEM"),
            sa.true(),
            sa.func.current_timestamp(),
        )
        .where(control.c.origen == "SALUTEM", control.c.medico_tratante != SIN_PROFESIONAL)
        .distinct()
    )
    op.execute(
        profesional.insert().from_select(["nombre", "origen", "activo", "created_at"], nombres)
    )


def upgrade() -> None:
    op.create_table(
        "profesional",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("especialidad", sa.String(length=80), nullable=True),
        sa.Column("origen", sa.String(length=10), nullable=False, server_default="SIGE"),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_profesional_nombre"),
    )
    _sembrar()


def downgrade() -> None:
    op.drop_table("profesional")
