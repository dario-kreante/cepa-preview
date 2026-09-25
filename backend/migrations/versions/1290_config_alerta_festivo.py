"""config_alerta y festivo: umbrales de alerta y festivos configurables (COMP-2609-07)

Siembra config_alerta con los valores que estaban fijos en el código
(``VENTANAS_DEFAULT`` de app/services/alertas.py; licencias 3 hábiles), provisorios
hasta que Coordinación los confirme (COMP-2609-13), y festivo con los feriados
nacionales de Chile 2026 y 2027.

Revision ID: 1290
Revises: 1280
"""

from datetime import date, datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "1290"
down_revision = "1280"
branch_labels = None
depends_on = None

# tipo, días, hábiles — copia de VENTANAS_DEFAULT al momento de la migración.
_CONFIG = [
    ("vencimiento_licencia", 3, True),
    ("plazo_ept", 5, True),
    ("plazo_isl", 5, True),
    ("receta_por_renovar", 5, False),
    ("oda_por_vencer", 7, False),
    ("control_medico", 7, False),
    ("consentimiento_pendiente", 30, False),
]

# Feriados nacionales. Los trasladables ya van en el lunes que corresponde.
# "(provisorio)": la fecha depende del solsticio o de un decreto y hay que confirmarla.
_FESTIVOS = [
    ("2026-01-01", "Año Nuevo"),
    ("2026-04-03", "Viernes Santo"),
    ("2026-04-04", "Sábado Santo"),
    ("2026-05-01", "Día Nacional del Trabajo"),
    ("2026-05-21", "Día de las Glorias Navales"),
    ("2026-06-21", "Día Nacional de los Pueblos Indígenas (provisorio)"),
    ("2026-06-29", "San Pedro y San Pablo"),
    ("2026-07-16", "Día de la Virgen del Carmen"),
    ("2026-08-15", "Asunción de la Virgen"),
    ("2026-09-18", "Independencia Nacional"),
    ("2026-09-19", "Día de las Glorias del Ejército"),
    ("2026-10-12", "Encuentro de Dos Mundos"),
    ("2026-10-31", "Día de las Iglesias Evangélicas y Protestantes"),
    ("2026-11-01", "Día de Todos los Santos"),
    ("2026-12-08", "Inmaculada Concepción"),
    ("2026-12-25", "Navidad"),
    ("2027-01-01", "Año Nuevo"),
    ("2027-03-26", "Viernes Santo"),
    ("2027-03-27", "Sábado Santo"),
    ("2027-05-01", "Día Nacional del Trabajo"),
    ("2027-05-21", "Día de las Glorias Navales"),
    ("2027-06-21", "Día Nacional de los Pueblos Indígenas (provisorio)"),
    ("2027-06-28", "San Pedro y San Pablo (trasladado; provisorio)"),
    ("2027-07-16", "Día de la Virgen del Carmen"),
    ("2027-08-15", "Asunción de la Virgen"),
    ("2027-09-18", "Independencia Nacional"),
    ("2027-09-19", "Día de las Glorias del Ejército"),
    ("2027-10-11", "Encuentro de Dos Mundos (trasladado; provisorio)"),
    ("2027-10-31", "Día de las Iglesias Evangélicas y Protestantes"),
    ("2027-11-01", "Día de Todos los Santos"),
    ("2027-12-08", "Inmaculada Concepción"),
    ("2027-12-25", "Navidad"),
]


def upgrade() -> None:
    config = op.create_table(
        "config_alerta",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("dias", sa.Integer(), nullable=False),
        sa.Column("habiles", sa.Boolean(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("actualizado_por", sa.String(length=120), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tipo", name="uq_config_alerta_tipo"),
    )
    festivo = op.create_table(
        "festivo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("fecha", name="uq_festivo_fecha"),
    )
    ahora = datetime.now(timezone.utc)
    op.bulk_insert(
        config,
        [
            {
                "tipo": tipo,
                "dias": dias,
                "habiles": habiles,
                "activo": True,
                "actualizado_por": "migracion",
                "updated_at": ahora,
            }
            for tipo, dias, habiles in _CONFIG
        ],
    )
    op.bulk_insert(
        festivo,
        [{"fecha": date.fromisoformat(f), "descripcion": d} for f, d in _FESTIVOS],
    )


def downgrade() -> None:
    op.drop_table("festivo")
    op.drop_table("config_alerta")
