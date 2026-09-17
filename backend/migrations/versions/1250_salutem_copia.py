"""Sync SALUTEM fase 1: copia local, checkpoint, bitácora, lease y columnas en ficha_clinica

Revision ID: 1250
Revises: 1240
"""

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from app.db.types import PortableJSON

revision = "1250"
down_revision = "1240"
branch_labels = None
depends_on = None


def _columnas_copia() -> list[sa.Column]:
    # Objetos nuevos en cada llamada: una Column no puede pertenecer a dos tablas.
    return [
        sa.Column("contenido", PortableJSON(), nullable=False),
        sa.Column("hash_contenido", sa.String(length=64), nullable=False),
        sa.Column("visto_primera_vez", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visto_ultima_vez", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cambiado_en", sa.DateTime(timezone=True), nullable=False),
    ]


def rellenar_salutem_cita_id(conn) -> int:
    """Copia contenido.citaId a la columna nueva en las fichas de SALUTEM.

    Se hace en Python porque en Oracle el JSON es un CLOB y no hay una
    expresión SQL portable para leerlo. Robusta y re-ejecutable: solo toca
    filas de SALUTEM aún sin rellenar, y salta silenciosamente contenido que
    no es un dict o cuyo citaId no es convertible a entero.
    """
    filas = conn.execute(
        sa.text(
            "SELECT id, contenido FROM ficha_clinica "
            "WHERE origen = 'SALUTEM' AND salutem_cita_id IS NULL"
        )
    ).all()
    rellenadas = 0
    for fila_id, contenido in filas:
        if hasattr(contenido, "read"):  # LOB de Oracle
            contenido = contenido.read()
        if isinstance(contenido, str):
            try:
                contenido = json.loads(contenido)
            except ValueError:
                continue
        if not isinstance(contenido, dict):
            continue
        cita_id = contenido.get("citaId")
        if cita_id is None:
            continue
        try:
            cita_id = int(cita_id)
        except (TypeError, ValueError):
            continue
        conn.execute(
            sa.text("UPDATE ficha_clinica SET salutem_cita_id = :cita WHERE id = :id"),
            {"cita": cita_id, "id": fila_id},
        )
        rellenadas += 1
    return rellenadas


def upgrade() -> None:
    op.create_table(
        "salutem_persona",
        sa.Column("salutem_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("rut", sa.String(length=12), nullable=True),
        *_columnas_copia(),
    )
    op.create_index("ix_salutem_persona_rut", "salutem_persona", ["rut"])

    op.create_table(
        "salutem_cita",
        sa.Column("cita_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_cita", sa.Date(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("estado_id", sa.Integer(), nullable=True),
        *_columnas_copia(),
        sa.Column("desaparecida_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_salutem_cita_persona_id", "salutem_cita", ["persona_id"])
    op.create_index("ix_salutem_cita_fecha_cita", "salutem_cita", ["fecha_cita"])

    op.create_table(
        "salutem_atencion",
        sa.Column("cita_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_cita", sa.Date(), nullable=True),
        *_columnas_copia(),
        sa.Column("hash_vinculado", sa.String(length=64), nullable=True),
        sa.Column("desaparecida_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_salutem_atencion_persona_id", "salutem_atencion", ["persona_id"])
    op.create_index("ix_salutem_atencion_fecha_cita", "salutem_atencion", ["fecha_cita"])

    op.create_table(
        "salutem_sync_dia",
        sa.Column("fecha", sa.Date(), primary_key=True),
        sa.Column("tipo", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("citas", sa.Integer(), nullable=False),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "salutem_sync_ejecucion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("modo", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("llamadas", sa.Integer(), nullable=False),
        sa.Column("nuevos", sa.Integer(), nullable=False),
        sa.Column("cambiados", sa.Integer(), nullable=False),
        sa.Column("desaparecidos", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=2000), nullable=True),
    )

    lease = op.create_table(
        "salutem_sync_lease",
        sa.Column("nombre", sa.String(length=30), primary_key=True),
        sa.Column("dueno", sa.String(length=80), nullable=True),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.bulk_insert(
        lease,
        [{"nombre": "salutem", "dueno": None, "vence_en": datetime(2000, 1, 1, tzinfo=timezone.utc)}],
    )

    op.add_column("ficha_clinica", sa.Column("salutem_cita_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "ficha_clinica",
        sa.Column("eliminada_en_origen", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ficha_clin_sal_cita", "ficha_clinica", ["salutem_cita_id"])
    rellenar_salutem_cita_id(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_ficha_clin_sal_cita", table_name="ficha_clinica")
    op.drop_column("ficha_clinica", "eliminada_en_origen")
    op.drop_column("ficha_clinica", "salutem_cita_id")
    op.drop_table("salutem_sync_lease")
    op.drop_table("salutem_sync_ejecucion")
    op.drop_table("salutem_sync_dia")
    op.drop_index("ix_salutem_atencion_fecha_cita", table_name="salutem_atencion")
    op.drop_index("ix_salutem_atencion_persona_id", table_name="salutem_atencion")
    op.drop_table("salutem_atencion")
    op.drop_index("ix_salutem_cita_fecha_cita", table_name="salutem_cita")
    op.drop_index("ix_salutem_cita_persona_id", table_name="salutem_cita")
    op.drop_table("salutem_cita")
    op.drop_index("ix_salutem_persona_rut", table_name="salutem_persona")
    op.drop_table("salutem_persona")
