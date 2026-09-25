"""gaf_tramo: catálogo de tramos de GAF (v5 D18, COMP-2609-12) y alerta por tramo (COMP-2609-20)

- Crea ``gaf_tramo`` sembrada con los 10 tramos EEAG de 10 en 10 (1-10 … 91-100), marcados
  ``provisorio`` hasta que Pilar confirme la segmentación (PA-v5-03).
- Agrega ``licencia_medica.eeag_gaf_tramo`` (el de control médico ya existe desde 1280).
- Rellena el tramo de las filas que ya tienen el GAF como entero (UPDATE portable con
  subconsulta correlacionada; los enteros se conservan). Un 0 no cae en ningún tramo y queda
  sin tramo: la tabla muestra el entero.
- Siembra ``config_alerta`` con el tipo ``gaf_licencia`` DESACTIVADO (CEPA-075 RN-2: sin
  criterio de la contraparte no se alerta). En ese tipo ``dias`` es el límite superior del
  tramo umbral: alerta si el tramo de la licencia está en o bajo él. 30 (tramos 1-10, 11-20 y
  21-30) es un valor provisorio a confirmar en COMP-2609-13.

Revision ID: 1300
Revises: 1290
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1300"
down_revision = "1290"
branch_labels = None
depends_on = None

UMBRAL_GAF_PROVISORIO = 30

# Portables (Postgres y Oracle 19c): sin funciones propias del motor.
SQL_RELLENO = [
    """
    UPDATE licencia_medica SET eeag_gaf_tramo = (
        SELECT t.etiqueta FROM gaf_tramo t
        WHERE licencia_medica.eeag_gaf BETWEEN t.desde AND t.hasta
    )
    WHERE eeag_gaf IS NOT NULL AND eeag_gaf_tramo IS NULL
    """,
    """
    UPDATE control_medico SET gaf_tramo = (
        SELECT t.etiqueta FROM gaf_tramo t
        WHERE control_medico.gaf BETWEEN t.desde AND t.hasta
    )
    WHERE gaf IS NOT NULL AND gaf_tramo IS NULL
    """,
]


def upgrade() -> None:
    tramo = op.create_table(
        "gaf_tramo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("desde", sa.Integer(), nullable=False),
        sa.Column("hasta", sa.Integer(), nullable=False),
        sa.Column("etiqueta", sa.String(length=10), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("provisorio", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("etiqueta", name="uq_gaf_tramo_etiqueta"),
        sa.CheckConstraint("desde < hasta", name="ck_gaf_tramo_rango"),
    )
    op.bulk_insert(
        tramo,
        [
            {
                "desde": desde,
                "hasta": desde + 9,
                "etiqueta": f"{desde}-{desde + 9}",
                "orden": i,
                "activo": True,
                "provisorio": True,
            }
            for i, desde in enumerate(range(1, 92, 10), start=1)
        ],
    )
    op.add_column(
        "licencia_medica", sa.Column("eeag_gaf_tramo", sa.String(length=10), nullable=True)
    )
    for sentencia in SQL_RELLENO:
        op.execute(sentencia)

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
                "tipo": "gaf_licencia",
                "dias": UMBRAL_GAF_PROVISORIO,
                "habiles": False,
                "activo": False,
                "actualizado_por": "migracion",
                "updated_at": datetime.now(timezone.utc),
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM config_alerta WHERE tipo = 'gaf_licencia'")
    op.execute("DELETE FROM alerta_notif WHERE tipo = 'gaf_licencia'")
    op.drop_column("licencia_medica", "eeag_gaf_tramo")
    op.drop_table("gaf_tramo")
