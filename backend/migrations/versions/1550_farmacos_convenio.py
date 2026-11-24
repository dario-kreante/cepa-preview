"""farmaco_canasta y farmaco_externalizado: catálogos de fármacos por convenio (QA-010/QA-013)

- ``farmaco_canasta``: canasta de fármacos del Convenio 002 (hoja «Canasta 2025» de la
  planilla de la clienta): código SAP, descripción, principio activo, bioequivalencia, marca,
  familia y laboratorio.
- ``farmaco_externalizado``: lista «Externalizado» (glosa de la prestación, truncada a 25
  caracteres como la entrega el ISL) con la marca de Convenio 001 y/o Convenio 002.

Son datos del sistema, no personales. Se siembran desde ``app/data/farmacos_convenio.json``,
generado una vez desde las planillas del QA del 23-11-2026, en lotes de 100 filas.

El downgrade borra ambas tablas.

Revision ID: 1550
Revises: 1530
"""
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "1550"
down_revision = "1530"
branch_labels = None
depends_on = None

_DATOS = Path(__file__).resolve().parents[2] / "app" / "data" / "farmacos_convenio.json"
_LOTE = 100


def _en_lotes(tabla, filas: list[dict]) -> None:
    for i in range(0, len(filas), _LOTE):
        op.bulk_insert(tabla, filas[i : i + _LOTE])


def upgrade() -> None:
    canasta = op.create_table(
        "farmaco_canasta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("codigo_sap", sa.String(20), nullable=False),
        sa.Column("descripcion", sa.String(120), nullable=False),
        sa.Column("principio_activo", sa.String(120), nullable=True),
        sa.Column("bioequivalencia", sa.String(5), nullable=True),
        sa.Column("detalle_be", sa.String(40), nullable=True),
        sa.Column("marca", sa.String(80), nullable=True),
        sa.Column("familia", sa.String(120), nullable=True),
        sa.Column("laboratorio", sa.String(120), nullable=True),
        sa.UniqueConstraint("codigo_sap", name="uq_farmaco_canasta_sap"),
    )
    externalizado = op.create_table(
        "farmaco_externalizado",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("glosa", sa.String(60), nullable=False),
        sa.Column("convenio_001", sa.Boolean(), nullable=False),
        sa.Column("convenio_002", sa.Boolean(), nullable=False),
    )

    datos = json.loads(_DATOS.read_text(encoding="utf-8"))
    columnas = ("codigo_sap", "descripcion", "principio_activo", "bioequivalencia",
                "detalle_be", "marca", "familia", "laboratorio")
    _en_lotes(canasta, [{c: f.get(c) for c in columnas} for f in datos["canasta_convenio_002"]])
    _en_lotes(
        externalizado,
        [
            {"glosa": f["glosa"], "convenio_001": bool(f["convenio_001"]),
             "convenio_002": bool(f["convenio_002"])}
            for f in datos["externalizado"]
        ],
    )


def downgrade() -> None:
    op.drop_table("farmaco_externalizado")
    op.drop_table("farmaco_canasta")
