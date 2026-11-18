"""oda: tipo de orden del reporte ISL y estado de gestión (QA-007, 16-11-2026)

- ``tipo_orden``: «Tipo de Orden» del reporte ISL (Ambulatoria = ODA; OPA/OPAEP = OPA). La
  carga lo llena desde ahora; las órdenes ya cargadas quedan en NULL (se muestran «—») hasta
  que se vuelva a subir el reporte ISL.
- ``estado_gestion``: pendiente (por defecto) | solicitada | recibida, editable desde el
  reporte de ODA vencidas.

El inicio de vigencia ya existía (``fecha_registro``, la carga lo llena con «Inicio Vigencia»).

Revision ID: 1470
Revises: 1460
"""
import sqlalchemy as sa
from alembic import op

revision = "1470"
down_revision = "1460"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("oda", sa.Column("tipo_orden", sa.String(40), nullable=True))
    op.add_column(
        "oda",
        sa.Column(
            "estado_gestion", sa.String(20), nullable=False, server_default="pendiente"
        ),
    )


def downgrade() -> None:
    op.drop_column("oda", "estado_gestion")
    op.drop_column("oda", "tipo_orden")
