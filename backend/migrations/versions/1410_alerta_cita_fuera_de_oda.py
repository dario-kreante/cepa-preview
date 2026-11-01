"""config_alerta: alerta de cita fuera de la vigencia de la ODA

Reunión de revisión 29-10-2026 (D9). El job diario de alertas revisa las citas de SALUTEM
agendadas o realizadas (7 días atrás y ``dias`` hacia adelante) de ingresos activos con
alguna ODA: si ninguna ODA del ingreso cubre la fecha de la cita, crea la alerta
``cita_fuera_de_oda``. Se resuelve sola cuando se carga una ODA que la cubre.

- Siembra ``config_alerta`` con el tipo ``cita_fuera_de_oda`` activo y 30 días hacia
  adelante.

El downgrade borra la configuración y las alertas de ese tipo.

Revision ID: 1410
Revises: 1400
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1410"
down_revision = "1400"
branch_labels = None
depends_on = None

TIPO = "cita_fuera_de_oda"


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
                "dias": 30,
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
