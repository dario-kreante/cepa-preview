"""cita_salutem: columnas de origen SALUTEM en ``cita`` y alerta de inasistencia (Fase 2)

- Agrega a ``cita``: ``salutem_cita_id`` (identificador de la cita en SALUTEM, único cuando no
  es nulo), ``origen`` (``SIGE`` por defecto; las filas existentes quedan en ``SIGE``),
  ``especialidad``, ``profesional_nombre`` y ``profesional_id`` (FK a ``profesional``).
- Siembra ``config_alerta`` con el tipo ``inasistencia`` activo, sin días de margen.

Revision ID: 1360
Revises: 1350
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1360"
down_revision = "1350"
branch_labels = None
depends_on = None

TIPO_INASISTENCIA = "inasistencia"


def upgrade() -> None:
    op.add_column("cita", sa.Column("salutem_cita_id", sa.BigInteger(), nullable=True))
    op.create_index(
        "uq_cita_salutem_cita_id", "cita", ["salutem_cita_id"], unique=True
    )
    op.add_column(
        "cita",
        sa.Column("origen", sa.String(length=10), nullable=False, server_default="SIGE"),
    )
    op.add_column("cita", sa.Column("especialidad", sa.String(length=80), nullable=True))
    op.add_column("cita", sa.Column("profesional_nombre", sa.String(length=160), nullable=True))
    op.add_column("cita", sa.Column("profesional_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_cita_profesional", "cita", "profesional", ["profesional_id"], ["id"]
    )

    config = sa.table(
        "config_alerta",
        sa.column("tipo", sa.String),
        sa.column("dias", sa.Integer),
        sa.column("habiles", sa.Boolean),
        sa.column("activo", sa.Boolean),
        sa.column("actualizado_por", sa.String),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        config,
        [
            {
                "tipo": TIPO_INASISTENCIA,
                "dias": 0,
                "habiles": False,
                "activo": True,
                "actualizado_por": "migracion",
                "updated_at": datetime.now(timezone.utc),
            }
        ],
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM config_alerta WHERE tipo = '{TIPO_INASISTENCIA}'")
    op.execute(f"DELETE FROM alerta_notif WHERE tipo = '{TIPO_INASISTENCIA}'")
    op.drop_constraint("fk_cita_profesional", "cita", type_="foreignkey")
    op.drop_column("cita", "profesional_id")
    op.drop_column("cita", "profesional_nombre")
    op.drop_column("cita", "especialidad")
    op.drop_column("cita", "origen")
    op.drop_index("uq_cita_salutem_cita_id", table_name="cita")
    op.drop_column("cita", "salutem_cita_id")
