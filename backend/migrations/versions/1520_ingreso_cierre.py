"""ingreso_cierre: historial de cierres y reaperturas del caso (QA-007, 23-11-2026)

Hasta ahora, al reabrir un caso se borraban el motivo y la fecha del cierre anterior del
ingreso (solo quedaban en la auditoría). Esta tabla guarda una fila por cada cierre; al
reabrir se completan ``reabierto_por`` / ``reabierto_en`` y el motivo de reapertura opcional.

Siembra una fila por cada ingreso hoy cerrado con motivo y fecha (los cerrados antes de
QA-011 no tienen motivo y no entran). ``fecha_cierre`` es el día del cierre; ``cerrado_en``
el instante.

El downgrade borra la tabla.

Revision ID: 1520
Revises: 1510
"""
import sqlalchemy as sa
from alembic import op

revision = "1520"
down_revision = "1510"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingreso_cierre",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("ingreso_id", sa.BigInteger(), sa.ForeignKey("ingreso.id"), nullable=False),
        sa.Column("motivo_cierre", sa.String(30), nullable=False),
        sa.Column("fecha_cierre", sa.Date(), nullable=False),
        sa.Column("cerrado_por", sa.String(100), nullable=False),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reabierto_por", sa.String(100), nullable=True),
        sa.Column("reabierto_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_reapertura", sa.String(300), nullable=True),
    )
    op.create_index("ix_ingreso_cierre_ingreso_id", "ingreso_cierre", ["ingreso_id"])
    # SQL estándar: vale igual en Oracle 19c y en Postgres.
    op.execute(
        "INSERT INTO ingreso_cierre (ingreso_id, motivo_cierre, fecha_cierre, cerrado_por, cerrado_en) "
        "SELECT id, motivo_cierre, CAST(fecha_cierre AS DATE), COALESCE(cierre_usuario, 'sistema'), fecha_cierre "
        "FROM ingreso "
        "WHERE estado = 'cerrado' AND motivo_cierre IS NOT NULL AND fecha_cierre IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_ingreso_cierre_ingreso_id", table_name="ingreso_cierre")
    op.drop_table("ingreso_cierre")
