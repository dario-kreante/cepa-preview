"""config_alerta: alerta de posible encuadre (2 o más inasistencias)

Reunión de revisión 29-10-2026 (D5/D6). Desde la 2.ª inasistencia de un paciente
(contando todo su historial) cada inasistencia nueva crea una alerta «posible encuadre»
para que el CEPA revise si pasa el ingreso al estado ``encuadre``.

- Siembra ``config_alerta`` con el tipo ``posible_encuadre`` activo, sin días de margen.
- El estado ``encuadre`` del ingreso no necesita migración: ``ingreso.estado`` es texto
  (String(20)) sin CHECK.

El downgrade borra la configuración y las alertas de ese tipo.

Revision ID: 1400
Revises: 1390
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1400"
down_revision = "1390"
branch_labels = None
depends_on = None

TIPO = "posible_encuadre"


def upgrade() -> None:
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
                "tipo": TIPO,
                "dias": 0,
                "habiles": False,
                "activo": True,
                "actualizado_por": "migracion",
                "updated_at": datetime.now(timezone.utc),
            }
        ],
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM config_alerta WHERE tipo = '{TIPO}'")
    op.execute(f"DELETE FROM alerta_notif WHERE tipo = '{TIPO}'")
