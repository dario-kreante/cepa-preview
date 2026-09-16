"""Migración 1250: copia de SALUTEM, checkpoint, bitácora, lease y columnas de ficha_clinica."""

import importlib.util
from pathlib import Path

from sqlalchemy import inspect

from app.db.session import engine
from app.models.ficha_clinica import FichaClinica
from app.models.salutem_sync import SalutemSyncLease


def _migracion():
    ruta = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "1250_salutem_copia.py"
    spec = importlib.util.spec_from_file_location("migracion_1250", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_tablas_del_sync_existen():
    insp = inspect(engine)
    for nombre in [
        "salutem_persona",
        "salutem_cita",
        "salutem_atencion",
        "salutem_sync_dia",
        "salutem_sync_ejecucion",
        "salutem_sync_lease",
    ]:
        assert insp.has_table(nombre), f"Falta la tabla {nombre!r}"
    columnas = {c["name"] for c in insp.get_columns("ficha_clinica")}
    assert {"salutem_cita_id", "eliminada_en_origen"} <= columnas


def test_el_lease_viene_sembrado_y_libre(db_session):
    lease = db_session.get(SalutemSyncLease, "salutem")
    assert lease is not None
    assert lease.dueno is None


def test_rellena_salutem_cita_id_desde_el_contenido(db_session, ingreso_fixture):
    de_salutem = FichaClinica(
        ingreso_id=ingreso_fixture.id,
        folio=ingreso_fixture.folio,
        origen="SALUTEM",
        contenido={"citaId": 425562},
    )
    de_push = FichaClinica(
        ingreso_id=ingreso_fixture.id,
        folio=ingreso_fixture.folio,
        origen="SAM",
        contenido={"citaId": 1},
    )
    db_session.add_all([de_salutem, de_push])
    db_session.flush()

    rellenadas = _migracion().rellenar_salutem_cita_id(db_session.connection())
    db_session.expire_all()

    assert rellenadas >= 1
    assert db_session.get(FichaClinica, de_salutem.id).salutem_cita_id == 425562
    assert db_session.get(FichaClinica, de_push.id).salutem_cita_id is None


def test_no_rompe_con_contenido_sin_cita_id(db_session, ingreso_fixture):
    sin_cita_id = FichaClinica(
        ingreso_id=ingreso_fixture.id,
        folio=ingreso_fixture.folio,
        origen="SALUTEM",
        contenido={"sin": "citaId"},
    )
    db_session.add(sin_cita_id)
    db_session.flush()

    _migracion().rellenar_salutem_cita_id(db_session.connection())
    db_session.expire_all()

    assert db_session.get(FichaClinica, sin_cita_id.id).salutem_cita_id is None


def test_no_rompe_con_cita_id_no_convertible_a_entero(db_session, ingreso_fixture):
    cita_id_invalido = FichaClinica(
        ingreso_id=ingreso_fixture.id,
        folio=ingreso_fixture.folio,
        origen="SALUTEM",
        contenido={"citaId": "no-numero"},
    )
    db_session.add(cita_id_invalido)
    db_session.flush()

    _migracion().rellenar_salutem_cita_id(db_session.connection())
    db_session.expire_all()

    assert db_session.get(FichaClinica, cita_id_invalido.id).salutem_cita_id is None
