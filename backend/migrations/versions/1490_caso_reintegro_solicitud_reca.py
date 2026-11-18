"""caso_reintegro: fecha de solicitud de RECA y alertas de reintegro (QA-003, 18-11-2026)

PRD v5 §7.4.2: el caso de reintegro registra «Solicitud de RECA (estado y fecha)».

- ``caso_reintegro.fecha_solicitud_reca``: cuándo se pidió la RECA. El estado se deriva
  (pendiente / solicitada / recibida) y no se guarda.
- Siembra ``config_alerta`` con ``reca_por_solicitar`` (activa, 5 días corridos desde la fecha
  del caso: PROVISIONAL, la clienta debe confirmarlo; se edita en la configuración de alertas)
  y ``proyeccion_reintegro`` (activa, sin plazo: la crea el sync de SALUTEM).

El downgrade borra la configuración, las alertas de esos tipos y la columna.

Revision ID: 1490
Revises: 1480
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1490"
down_revision = "1480"
branch_labels = None
depends_on = None

TIPOS = {"reca_por_solicitar": 5, "proyeccion_reintegro": 0}


def upgrade() -> None:
    op.add_column("caso_reintegro", sa.Column("fecha_solicitud_reca", sa.Date(), nullable=True))
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
                "tipo": tipo,
                "dias": dias,
                "habiles": False,
                "activo": True,
                "actualizado_por": "migracion",
                "updated_at": datetime.now(timezone.utc),
            }
            for tipo, dias in TIPOS.items()
        ],
    )


def downgrade() -> None:
    for tipo in TIPOS:
        op.execute(f"DELETE FROM config_alerta WHERE tipo = '{tipo}'")
        op.execute(f"DELETE FROM alerta_notif WHERE tipo = '{tipo}'")
    op.drop_column("caso_reintegro", "fecha_solicitud_reca")
