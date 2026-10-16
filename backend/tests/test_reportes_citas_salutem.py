"""Fase 2 (cita desde SALUTEM) — Tarea 4: los reportes cuentan solo citas SALUTEM.

Spec decisiones 4, 8, 10 y 11: filtro de origen y especialidades, nuevo denominador de
adherencia y carga agrupada por quien atendió (cita.profesional_nombre).
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente

_ING = dict(
    folio_manual=True,
    tipo_derivacion="DIAT",
    tipo_ingreso="convenio",
    modelo_tratamiento="ambulatorio",
    diagnostico="Test",
    programa="DIEP",
    tipo_convenio="DIEP",
    fecha_ingreso=date(2026, 1, 1),
)
_P = {"fecha_desde": "2026-05-01", "fecha_hasta": "2026-05-31"}


def _ingreso(db, rut: str, folio: str, **kw) -> Ingreso:
    pac = Paciente(rut=rut, nombre="Test", sexo="F", edad=30, region="Maule")
    db.add(pac)
    db.flush()
    ing = Ingreso(paciente_id=pac.id, folio=folio, **{**_ING, **kw})
    db.add(ing)
    db.flush()
    return ing


def _cita(db, ing, estado="realizada", origen="SALUTEM", dia=10, **kw) -> Cita:
    c = Cita(ingreso_id=ing.id, estado=estado, fecha=date(2026, 5, dia), origen=origen, **kw)
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def ing(db_session):
    return _ingreso(db_session, "81000001-1", "F-RSA-001")


# ── Foco 4: las citas origen SIGE no cuentan en ningún reporte ───────────────

def test_adherencia_ignora_citas_origen_sige(as_coordinacion, db_session, ing):
    _cita(db_session, ing, "realizada", "SALUTEM")
    _cita(db_session, ing, "inasistencia", "SIGE")
    _cita(db_session, ing, "realizada", "SIGE")
    db_session.commit()
    body = as_coordinacion.get(f"/api/v1/reportes/adherencia/{ing.id}").json()
    assert body["citas_agendadas"] == 1
    assert body["citas_realizadas"] == 1
    assert body["pct_adherencia"] == 100.0


def test_operativo_ignora_citas_origen_sige(as_coordinacion, db_session, ing):
    _cita(db_session, ing, "realizada", "SALUTEM")
    _cita(db_session, ing, "realizada", "SIGE")
    _cita(db_session, ing, "anulada", "SIGE")
    db_session.commit()
    body = as_coordinacion.get("/api/v1/reportes/operativo", params=_P).json()
    assert body["totales"]["realizadas"] == 1
    assert body["totales"]["anuladas"] == 0
    assert sum(d["total_citas"] for d in body["items"]) == 1


def test_convenio_ignora_citas_origen_sige(as_coordinacion, db_session, ing):
    _cita(db_session, ing, "realizada", "SALUTEM")
    _cita(db_session, ing, "realizada", "SIGE")
    _cita(db_session, ing, "inasistencia", "SIGE")
    db_session.commit()
    body = as_coordinacion.get(
        "/api/v1/reportes/convenio", params={**_P, "tipo_convenio": "DIEP"}
    ).json()
    item = body["items"][0]
    assert item["total_atenciones"] == 1
    assert item["total_inasistencias"] == 0


def test_carga_ignora_citas_origen_sige(as_coordinacion, db_session, ing):
    _cita(db_session, ing, "realizada", "SALUTEM", profesional_nombre="Ana Pérez")
    _cita(db_session, ing, "realizada", "SIGE", profesional_nombre="Otro Prof")
    db_session.commit()
    items = as_coordinacion.get("/api/v1/reportes/carga-laboral", params=_P).json()["items"]
    assert [i["nombre_profesional"] for i in items] == ["Ana Pérez"]
    assert items[0]["total_atenciones"] == 1


def test_dashboard_ignora_citas_origen_sige(as_coordinacion, db_session, ing):
    _cita(db_session, ing, "realizada", "SALUTEM")
    _cita(db_session, ing, "realizada", "SIGE")
    _cita(db_session, ing, "inasistencia", "SIGE")
    db_session.commit()
    body = as_coordinacion.get("/api/v1/dashboard", params=_P).json()
    assert body["total_atenciones"] == 1
    assert body["total_inasistencias"] == 0
    assert body["cumplimiento_convenios"] == [{"tipo_convenio": "DIEP", "total_realizadas": 1}]


# ── Decisión 4: filtro de especialidades configurado ─────────────────────────

def test_filtro_especialidades_reportes(as_coordinacion, db_session, ing, monkeypatch):
    _cita(db_session, ing, "realizada", especialidad="Psicología ")
    _cita(db_session, ing, "realizada", especialidad="Médico/a")
    _cita(db_session, ing, "realizada", especialidad=None)
    db_session.commit()

    # Sin configuración: todas las especialidades cuentan.
    body = as_coordinacion.get("/api/v1/reportes/operativo", params=_P).json()
    assert body["totales"]["realizadas"] == 3

    monkeypatch.setattr(
        "app.services.reportes_filtros.get_settings",
        lambda: SimpleNamespace(citas_especialidades_reportes_set=frozenset({"psicología"})),
    )
    body = as_coordinacion.get("/api/v1/reportes/operativo", params=_P).json()
    assert body["totales"]["realizadas"] == 1
    body = as_coordinacion.get("/api/v1/dashboard", params=_P).json()
    assert body["total_atenciones"] == 1


def test_filtro_especialidades_en_adherencia_convenio_y_carga(
    as_coordinacion, db_session, ing, monkeypatch
):
    _cita(db_session, ing, "realizada", especialidad="Psicología", profesional_nombre="Ana", dia=1)
    _cita(db_session, ing, "realizada", especialidad="Médico/a", profesional_nombre="Bea", dia=2)
    _cita(db_session, ing, "inasistencia", especialidad="Médico/a", profesional_nombre="Bea", dia=3)
    db_session.commit()
    monkeypatch.setattr(
        "app.services.reportes_filtros.get_settings",
        lambda: SimpleNamespace(citas_especialidades_reportes_set=frozenset({"psicología"})),
    )

    adh = as_coordinacion.get(f"/api/v1/reportes/adherencia/{ing.id}").json()
    assert (adh["citas_agendadas"], adh["citas_realizadas"]) == (1, 1)

    conv = as_coordinacion.get(
        "/api/v1/reportes/convenio", params={**_P, "tipo_convenio": "DIEP"}
    ).json()["items"][0]
    assert (conv["total_atenciones"], conv["total_inasistencias"]) == (1, 0)

    carga = as_coordinacion.get("/api/v1/reportes/carga-laboral", params=_P).json()["items"]
    assert [(i["nombre_profesional"], i["total_atenciones"]) for i in carga] == [("Ana", 1)]


def test_condicion_citas_reportables_sin_join(db_session, ing):
    from app.services.reportes_filtros import condicion_citas_reportables

    _cita(db_session, ing, "realizada", "SALUTEM")
    _cita(db_session, ing, "realizada", "SIGE")
    n = db_session.execute(
        select(func.count()).select_from(Cita).where(condicion_citas_reportables())
    ).scalar_one()
    assert n == 1


# ── Decisión 10: denominador de adherencia ───────────────────────────────────

def test_adherencia_excluye_anuladas_y_agendadas(as_coordinacion, db_session, ing):
    _cita(db_session, ing, "realizada", dia=1)
    _cita(db_session, ing, "realizada", dia=2)
    _cita(db_session, ing, "inasistencia", dia=3)
    _cita(db_session, ing, "anulada", dia=4)
    _cita(db_session, ing, "agendada", dia=5)
    db_session.commit()
    body = as_coordinacion.get(f"/api/v1/reportes/adherencia/{ing.id}").json()
    assert body["citas_agendadas"] == 3
    assert body["citas_realizadas"] == 2
    assert body["pct_adherencia"] == pytest.approx(66.67, abs=0.01)


def test_adherencia_solo_anuladas_es_none(as_coordinacion, db_session, ing):
    _cita(db_session, ing, "anulada", dia=1)
    _cita(db_session, ing, "agendada", dia=2)
    db_session.commit()
    body = as_coordinacion.get(f"/api/v1/reportes/adherencia/{ing.id}").json()
    assert body["citas_agendadas"] == 0
    assert body["pct_adherencia"] is None


# ── Decisión 11: carga por quien atendió ─────────────────────────────────────

def test_carga_agrupa_por_profesional_nombre(as_coordinacion, db_session, ing):
    ing2 = _ingreso(db_session, "81000002-2", "F-RSA-002")
    # Profesional fuera del catálogo: profesional_id nulo; mismo nombre con espacios.
    _cita(db_session, ing, "realizada", profesional_nombre="Ana Pérez", especialidad="Psicología", dia=1)
    _cita(db_session, ing, "inasistencia", profesional_nombre=" Ana Pérez ", especialidad="Psicología", dia=2)
    _cita(db_session, ing2, "realizada", profesional_nombre="Ana Pérez", especialidad="Psicología", dia=3)
    # Sin nombre: se agrupan juntas.
    _cita(db_session, ing, "realizada", dia=4)
    _cita(db_session, ing2, "realizada", profesional_nombre="   ", dia=5)
    db_session.commit()

    items = as_coordinacion.get("/api/v1/reportes/carga-laboral", params=_P).json()["items"]
    por_nombre = {i["nombre_profesional"]: i for i in items}
    assert set(por_nombre) == {"Ana Pérez", "Sin profesional informado"}
    ana = por_nombre["Ana Pérez"]
    assert ana["profesional_id"] is None
    assert ana["especialidad"] == "Psicología"
    assert ana["total_casos"] == 2
    assert ana["total_atenciones"] == 2
    sin = por_nombre["Sin profesional informado"]
    assert sin["total_casos"] == 2
    assert sin["total_atenciones"] == 2


def test_carga_incluye_profesional_id_del_catalogo(as_coordinacion, db_session, ing):
    from app.models.profesional import Profesional

    prof = Profesional(nombre="Luis Soto")
    db_session.add(prof)
    db_session.flush()
    _cita(db_session, ing, "realizada", profesional_nombre="Luis Soto", profesional_id=prof.id)
    db_session.commit()
    items = as_coordinacion.get("/api/v1/reportes/carga-laboral", params=_P).json()["items"]
    assert items[0]["profesional_id"] == prof.id
    assert items[0]["nombre_profesional"] == "Luis Soto"
