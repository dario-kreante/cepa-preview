"""QA-004 — Reporte de ingresos del período (una fila por ingreso + pendientes de folio)."""
from datetime import date, datetime, timezone

import pytest

URL = "/api/v1/reportes/ingresos"


def _paciente(db, rut, nombre, region="Maule", estado="completo", creado=None):
    from app.models.paciente import Paciente

    p = Paciente(rut=rut, nombre=nombre, region=region, estado_registro=estado)
    if creado is not None:
        p.created_at = creado
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente, folio, fecha, tipo="convenio", programa="DIEP", convenio="ISL"):
    from app.models.ingreso import Ingreso

    i = Ingreso(
        paciente_id=paciente.id, folio=folio, folio_manual=True, fecha_ingreso=fecha,
        tipo_derivacion="DIAT", tipo_ingreso=tipo, programa=programa, tipo_convenio=convenio,
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def datos(db_session):
    a = _paciente(db_session, "11111111-1", "Ana Uno", region="Maule")
    b = _paciente(db_session, "22222222-2", "Beto Dos", region="Ñuble")
    c = _paciente(db_session, "33333333-3", "Carla Tres", region="Maule")
    _ingreso(db_session, a, "F-1", date(2026, 11, 10), tipo="convenio", programa="DIEP", convenio="ISL")
    _ingreso(db_session, b, "F-2", date(2026, 11, 12), tipo="particular", programa="PAPT", convenio="ACHS")
    _ingreso(db_session, c, "F-OUT", date(2026, 10, 1))  # fuera del período
    # Borrador pendiente creado dentro del período (hora de Chile 12-11 → dentro)
    _paciente(db_session, None, "Pendiente Cuatro", region=None, estado="pendiente_folio",
              creado=datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc))
    # Borrador pendiente creado fuera del período
    _paciente(db_session, None, "Pendiente Viejo", estado="pendiente_folio",
              creado=datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc))
    # Descartado dentro del período: no cuenta
    _paciente(db_session, None, "Descartado", estado="descartado",
              creado=datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc))
    db_session.commit()


def _get(client, desde="2026-11-09", hasta="2026-11-15"):
    return client.get(URL, params={"fecha_desde": desde, "fecha_hasta": hasta})


def test_una_fila_por_ingreso_y_pendientes(as_coordinacion, datos):
    r = _get(as_coordinacion)
    assert r.status_code == 200
    body = r.json()
    assert body["periodo_desde"] == "2026-11-09"
    assert body["periodo_hasta"] == "2026-11-15"
    assert body["total"] == 3
    assert body["total_con_folio"] == 2
    assert body["total_pendientes"] == 1
    nombres = {i["paciente_nombre"]: i for i in body["items"]}
    assert set(nombres) == {"Ana Uno", "Beto Dos", "Pendiente Cuatro"}
    ana = nombres["Ana Uno"]
    assert ana["paciente_rut"] == "11111111-1"
    assert ana["folio"] == "F-1"
    assert ana["pendiente"] is False
    assert ana["tipo_ingreso"] == "convenio"
    assert ana["programa"] == "DIEP"
    assert ana["region"] == "Maule"
    pen = nombres["Pendiente Cuatro"]
    assert pen["pendiente"] is True
    assert pen["folio"] is None
    assert pen["tipo_ingreso"] is None


def test_totales_por_dimension(as_coordinacion, datos):
    body = _get(as_coordinacion).json()

    def como_dict(lista):
        return {x["etiqueta"]: x["total"] for x in lista}

    assert como_dict(body["por_tipo_ingreso"]) == {
        "convenio": 1, "particular": 1, "Pendiente de folio": 1,
    }
    assert como_dict(body["por_region"]) == {"Maule": 1, "Ñuble": 1, "Sin región": 1}
    assert como_dict(body["por_programa"]) == {"DIEP": 1, "PAPT": 1, "Sin programa": 1}
    assert como_dict(body["por_convenio"]) == {"ISL": 1, "ACHS": 1, "Sin convenio": 1}


def test_periodo_incluye_extremos_y_excluye_fuera(as_coordinacion, datos):
    body = _get(as_coordinacion, "2026-11-10", "2026-11-10").json()
    assert [i["folio"] for i in body["items"]] == ["F-1"]
    assert body["total_pendientes"] == 0


def test_pendiente_con_ingreso_en_periodo_no_se_cuenta_dos_veces(as_coordinacion, db_session):
    p = _paciente(db_session, "44444444-4", "Doble", estado="pendiente_folio",
                  creado=datetime(2026, 11, 11, 15, 0, tzinfo=timezone.utc))
    _ingreso(db_session, p, "F-DOBLE", date(2026, 11, 11))
    db_session.commit()
    body = _get(as_coordinacion).json()
    assert body["total"] == 1
    assert body["total_pendientes"] == 0
    assert body["items"][0]["folio"] == "F-DOBLE"
    assert body["items"][0]["pendiente"] is False


def test_paciente_con_dos_ingresos_da_dos_filas(as_coordinacion, db_session):
    p = _paciente(db_session, "55555555-5", "Reingresa")
    _ingreso(db_session, p, "F-A", date(2026, 11, 10))
    _ingreso(db_session, p, "F-B", date(2026, 11, 11))
    db_session.commit()
    assert _get(as_coordinacion).json()["total"] == 2


def test_periodo_invertido_422(as_coordinacion):
    assert _get(as_coordinacion, "2026-11-15", "2026-11-09").status_code == 422


def test_sin_fechas_usa_30_dias(as_coordinacion):
    r = as_coordinacion.get(URL)
    assert r.status_code == 200
    body = r.json()
    desde = date.fromisoformat(body["periodo_desde"])
    hasta = date.fromisoformat(body["periodo_hasta"])
    assert (hasta - desde).days == 29


def test_permisos(as_auditor, as_admin, as_superadmin, client):
    assert _get(as_auditor).status_code == 200
    assert _get(as_admin).status_code == 200
    assert _get(as_superadmin).status_code == 200
    assert client.get(URL).status_code in (401, 403)


def test_rol_sin_permiso_403(client, db_session):
    from tests.conftest import _cliente_autenticado

    c = _cliente_autenticado(client, db_session, "otro_rol", "Profesional")
    assert _get(c).status_code == 403


def test_auditoria_registrada(as_coordinacion, db_session, datos):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    _get(as_coordinacion)
    filas = db_session.execute(
        select(AuditLog).where(AuditLog.entity == "reporte_ingresos")
    ).scalars().all()
    assert len(filas) == 1


def test_compila_en_oracle():
    from sqlalchemy.dialects import oracle
    from app.routers.reporte_ingresos import _consulta_ingresos, _consulta_pendientes

    d, h = date(2026, 11, 9), date(2026, 11, 15)
    for stmt in (_consulta_ingresos(d, h), _consulta_pendientes(d, h)):
        str(stmt.compile(dialect=oracle.dialect()))
