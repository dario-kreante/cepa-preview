"""Migración 1530 (QA-010): ocupación, fecha de remisión a ISL, alerta «Pendiente de remitir a
ISL» y plazo de 15 días de «RECA por solicitar».

Archivo aparte: el downgrade no puede correr con una sesión de prueba abierta que tenga filas
de config_alerta bloqueadas.
"""

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.config_alerta import ConfigAlerta

TIPO = "pendiente_remitir_isl"


def test_columnas_nuevas_nullable():
    cols = {c["name"]: c for c in inspect(engine).get_columns("caso_reintegro")}
    assert cols["ocupacion"]["nullable"] is True and cols["ocupacion"]["type"].length == 120
    assert cols["fecha_remitido_isl"]["nullable"] is True


def test_siembra_la_configuracion(db_session: Session):
    fila = db_session.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == TIPO))
    assert (fila.dias, fila.habiles, fila.activo) == (7, False, True)


def test_la_migracion_sube_y_baja_y_respeta_un_plazo_editado():
    from alembic import command  # noqa: PLC0415

    from tests.conftest import _alembic_config  # noqa: PLC0415

    cfg = _alembic_config()
    command.downgrade(cfg, "1520")
    try:
        assert "ocupacion" not in {c["name"] for c in inspect(engine).get_columns("caso_reintegro")}
        with Session(bind=engine) as s:
            filas = {c.tipo: c for c in s.scalars(select(ConfigAlerta))}
            assert TIPO not in filas
            assert filas["reca_por_solicitar"].dias == 5
            filas["reca_por_solicitar"].dias = 9  # Coordinación ya lo había cambiado
            s.commit()
        command.upgrade(cfg, "head")
        with Session(bind=engine) as s:
            assert s.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == "reca_por_solicitar")).dias == 9
            s.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == "reca_por_solicitar")).dias = 15
            s.commit()
    finally:
        command.upgrade(cfg, "head")
    assert "fecha_remitido_isl" in {c["name"] for c in inspect(engine).get_columns("caso_reintegro")}
