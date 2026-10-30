"""config_alerta: alerta del plazo de insumos de la empresa (proceso EPT)

Reunión de revisión 29-10-2026 (D10). El empleador entrega los documentos («insumos») que
el CEPA envía al EPTista para elaborar el informe. El plazo ya se registra en el proceso
EPT (``proceso_ept.plazo_insumos_empresa``); faltaba el recordatorio el mismo día, para
todos los casos que vencen ese día.

- Siembra ``config_alerta`` con el tipo ``plazo_insumos_ept`` activo y 0 días de margen
  (avisa el mismo día).

El downgrade borra la configuración y las alertas de ese tipo.

Revision ID: 1420
Revises: 1410
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1420"
down_revision = "1410"
branch_labels = None
depends_on = None

TIPO = "plazo_insumos_ept"


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
