"""Migración 1490 (QA-003): fecha de solicitud de RECA y configuración de las dos alertas nuevas."""

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.config_alerta import ConfigAlerta


def test_columna_fecha_solicitud_reca_nullable():
    cols = {c["name"]: c for c in inspect(engine).get_columns("caso_reintegro")}
    assert cols["fecha_solicitud_reca"]["nullable"] is True


def test_siembra_la_configuracion_de_las_alertas(db_session: Session):
    filas = {c.tipo: c for c in db_session.scalars(select(ConfigAlerta))}
    reca, proyeccion = filas["reca_por_solicitar"], filas["proyeccion_reintegro"]
    # 1490 sembró 5 días (provisional); 1530 lo sube a 15 (QA-010).
    assert (reca.dias, reca.habiles, reca.activo) == (15, False, True)
    assert (proyeccion.dias, proyeccion.habiles, proyeccion.activo) == (0, False, True)


def test_la_migracion_sube_y_baja_sin_perder_datos():
    from alembic import command  # noqa: PLC0415

    from tests.conftest import _alembic_config  # noqa: PLC0415

    cfg = _alembic_config()
    command.downgrade(cfg, "1480")
    try:
        assert "fecha_solicitud_reca" not in {c["name"] for c in inspect(engine).get_columns("caso_reintegro")}
        with Session(bind=engine) as s:
            tipos = set(s.scalars(select(ConfigAlerta.tipo)))
            assert not tipos & {"reca_por_solicitar", "proyeccion_reintegro"}
    finally:
        command.upgrade(cfg, "head")
    assert "fecha_solicitud_reca" in {c["name"] for c in inspect(engine).get_columns("caso_reintegro")}
