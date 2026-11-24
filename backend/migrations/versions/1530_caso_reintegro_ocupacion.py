"""caso_reintegro: ocupación, fecha de remisión a ISL y plazos de reintegro (QA-010, 23-11-2026)

- ``caso_reintegro.ocupacion`` (String 120, nullable): ocupación del trabajador, editable en el
  alta del caso y precargada desde un caso anterior del paciente o desde SALUTEM.
- ``caso_reintegro.fecha_remitido_isl`` (Date, nullable): cuándo se remitió el caso a ISL. Se
  puede marcar sin cerrar el caso.
- Siembra ``config_alerta`` con ``pendiente_remitir_isl`` (activa, 7 días corridos desde la fecha
  del caso).
- ``reca_por_solicitar`` pasa de 5 a 15 días corridos (QA-010: la clienta lo confirmó, contados
  desde la fecha de envío del caso EPT). Solo si sigue en el valor sembrado (5): si Coordinación
  ya lo cambió, se respeta.

El downgrade devuelve el plazo de RECA a 5 (si sigue en 15), borra la configuración y las
alertas del tipo nuevo y las dos columnas.

Revision ID: 1530
Revises: 1520
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1530"
down_revision = "1520"
branch_labels = None
depends_on = None

TIPO_REMITIR = "pendiente_remitir_isl"


def upgrade() -> None:
    op.add_column("caso_reintegro", sa.Column("ocupacion", sa.String(120), nullable=True))
    op.add_column("caso_reintegro", sa.Column("fecha_remitido_isl", sa.Date(), nullable=True))
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
                "tipo": TIPO_REMITIR,
                "dias": 7,
                "habiles": False,
                "activo": True,
                "actualizado_por": "migracion",
                "updated_at": datetime.now(timezone.utc),
            }
        ],
    )
    op.execute("UPDATE config_alerta SET dias = 15 WHERE tipo = 'reca_por_solicitar' AND dias = 5")


def downgrade() -> None:
    op.execute("UPDATE config_alerta SET dias = 5 WHERE tipo = 'reca_por_solicitar' AND dias = 15")
    op.execute(f"DELETE FROM config_alerta WHERE tipo = '{TIPO_REMITIR}'")
    op.execute(f"DELETE FROM alerta_notif WHERE tipo = '{TIPO_REMITIR}'")
    op.drop_column("caso_reintegro", "fecha_remitido_isl")
    op.drop_column("caso_reintegro", "ocupacion")
