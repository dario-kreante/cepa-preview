"""QA-006 / QA-007 (registro de pruebas del 16-11): reporte de ODA por paciente, ODA vencidas
con gestión, filtro por programa, Excel y cruce de cobertura contra las atenciones.
"""

import io
from pathlib import Path
from datetime import date, timedelta

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.models.paciente import Paciente

HOY = date.today()
_n = 0


def _d(dias: int) -> date:
    return HOY + timedelta(days=dias)


def _caso(db, *, nombre=None, rut="__auto__", programa="Programa Regular", estado="activo",
          fecha_ingreso=date(2026, 1, 5)) -> Ingreso:
    global _n
    _n += 1
    if rut == "__auto__":
        rut = f"{10_000_000 + _n}-K"
    p = Paciente(rut=rut, nombre=nombre or f"Paciente {_n}", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    ing = Ingreso(
        paciente_id=p.id, folio=f"F-QA-{_n}", folio_manual=True, programa=programa,
        fecha_ingreso=fecha_ingreso, tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="t", estado=estado,
    )
    db.add(ing)
    db.flush()
    return ing


def _oda(db, ing, ident, inicio, fin, *, tipo="OPA", vigente=True) -> Oda:
    o = Oda(
        ingreso_id=ing.id, identificador=ident, fecha_registro=inicio, fecha_vencimiento=fin,
        vigente=vigente, tipo_orden=tipo,
    )
    db.add(o)
    db.flush()
    return o


def _cita(db, ing, fecha, estado="realizada") -> None:
    db.add(Cita(ingreso_id=ing.id, estado=estado, fecha=fecha))
    db.flush()


def _fila(cliente, nombre_paciente, **params):
    r = cliente.get("/api/v1/reportes/odas-vencidas", params=params)
    assert r.status_code == 200, r.text
    filas = [i for i in r.json()["items"] if i["paciente_nombre"] == nombre_paciente]
    assert len(filas) == 1, r.json()["items"]
    return filas[0]


# ── Cobertura (cruce con las atenciones) ───────────────────────────────────────


def test_cubre_si_todas_las_atenciones_caen_dentro_de_la_orden(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Cubierta")
    _oda(db_session, ing, "1001", _d(-40), _d(-20))
    _cita(db_session, ing, _d(-30))
    db_session.commit()
    f = _fila(as_coordinacion, "Cubierta")
    assert f["cobertura"] == "CUBRE"
    assert f["fechas_atencion"] == [_d(-30).isoformat()]


def test_solicitar_si_una_atencion_queda_fuera_de_toda_orden(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Descubierta")
    _oda(db_session, ing, "1002", _d(-40), _d(-20))
    _cita(db_session, ing, _d(-30))
    _cita(db_session, ing, _d(-5))
    db_session.commit()
    f = _fila(as_coordinacion, "Descubierta")
    assert f["cobertura"] == "SOLICITAR"
    assert f["fechas_atencion"] == [_d(-30).isoformat(), _d(-5).isoformat()]


def test_solicitar_sin_atenciones_porque_hoy_no_hay_orden_vigente(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Sin atenciones")
    _oda(db_session, ing, "1003", _d(-40), _d(-20))
    db_session.commit()
    f = _fila(as_coordinacion, "Sin atenciones")
    assert f["cobertura"] == "SOLICITAR"
    assert f["fechas_atencion"] == []


def test_solo_cuentan_citas_realizadas(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Solo realizadas")
    _oda(db_session, ing, "1004", _d(-40), _d(-20))
    _cita(db_session, ing, _d(-30))
    _cita(db_session, ing, _d(-5), estado="inasistencia")
    _cita(db_session, ing, _d(-4), estado="anulada")
    db_session.commit()
    f = _fila(as_coordinacion, "Solo realizadas")
    assert f["cobertura"] == "CUBRE"
    assert f["fechas_atencion"] == [_d(-30).isoformat()]


def test_una_fila_por_paciente_con_varias_ordenes(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Dos órdenes")
    _oda(db_session, ing, "2001", _d(-60), _d(-30), tipo="Ambulatoria", vigente=False)
    _oda(db_session, ing, "2002", _d(-35), _d(-20), tipo="OPAEP")
    _cita(db_session, ing, _d(-32))  # solo la cubre 2001
    _cita(db_session, ing, _d(-25))  # solo la cubre 2002
    db_session.commit()
    f = _fila(as_coordinacion, "Dos órdenes")
    assert f["cobertura"] == "CUBRE"
    assert [(o["identificador"], o["tipo"]) for o in f["ordenes"]] == [
        ("2001", "ODA"),
        ("2002", "OPA"),
    ]
    assert f["ordenes"][0]["fecha_inicio"] == _d(-60).isoformat()
    assert f["ordenes"][1]["fecha_termino"] == _d(-20).isoformat()


def test_orden_sin_tipo_ni_inicio_se_muestra_vacia_sin_inventar(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Dato antiguo")
    _oda(db_session, ing, "3001", None, _d(-20), tipo=None)
    _cita(db_session, ing, _d(-5))
    db_session.commit()
    f = _fila(as_coordinacion, "Dato antiguo")
    assert f["ordenes"] == [
        {"identificador": "3001", "tipo": None, "fecha_inicio": None,
         "fecha_termino": _d(-20).isoformat()}
    ]
    assert f["cobertura"] == "SOLICITAR"


# ── Filtro por programa ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "filtro,guardado",
    [("regular", "Programa Regular"), ("ley_karin", "Ley Karin"), ("pipt", "PIPT")],
)
def test_filtra_por_programa(as_coordinacion, db_session, filtro, guardado):
    for prog in ("Programa Regular", "Ley Karin", "PIPT", "DIEP", None):
        ing = _caso(db_session, nombre=f"P-{prog}", programa=prog)
        _oda(db_session, ing, f"9{_n}", _d(-40), _d(-20))
    db_session.commit()
    r = as_coordinacion.get("/api/v1/reportes/odas-vencidas", params={"programa": filtro})
    assert r.status_code == 200
    assert {i["paciente_nombre"] for i in r.json()["items"]} == {f"P-{guardado}"}


def test_filtro_por_programa_acepta_variantes_de_escritura(as_coordinacion, db_session):
    for prog in ("REGULAR", "Ley karin", "pipt"):
        ing = _caso(db_session, nombre=f"V-{prog}", programa=prog)
        _oda(db_session, ing, f"8{_n}", _d(-40), _d(-20))
    db_session.commit()
    for filtro, esperado in (("regular", "V-REGULAR"), ("ley_karin", "V-Ley karin"), ("pipt", "V-pipt")):
        r = as_coordinacion.get("/api/v1/reportes/odas-vencidas", params={"programa": filtro})
        assert {i["paciente_nombre"] for i in r.json()["items"]} == {esperado}


# ── Estado de gestión ──────────────────────────────────────────────────────────


def test_gestion_por_defecto_pendiente(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Gestión base")
    _oda(db_session, ing, "4001", _d(-40), _d(-20))
    db_session.commit()
    f = _fila(as_coordinacion, "Gestión base")
    assert f["estado_gestion"] == "pendiente"


def test_escritor_cambia_la_gestion_y_queda_auditado(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Gestión cambia")
    oda = _oda(db_session, ing, "4002", _d(-40), _d(-20))
    db_session.commit()
    r = as_coordinacion.patch(f"/api/v1/odas/{oda.id}/gestion", json={"estado_gestion": "solicitada"})
    assert r.status_code == 200, r.text
    assert r.json()["estado_gestion"] == "solicitada"
    assert _fila(as_coordinacion, "Gestión cambia")["estado_gestion"] == "solicitada"
    traza = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "oda", AuditLog.entity_id == str(oda.id))
    ).all()
    assert [(t.action, t.valor_anterior, t.valor_nuevo) for t in traza] == [
        ("UPDATE", "pendiente", "solicitada")
    ]


def test_gestion_rechaza_estado_invalido(as_coordinacion, db_session):
    ing = _caso(db_session)
    oda = _oda(db_session, ing, "4003", _d(-40), _d(-20))
    db_session.commit()
    r = as_coordinacion.patch(f"/api/v1/odas/{oda.id}/gestion", json={"estado_gestion": "inventado"})
    assert r.status_code == 422


def test_auditor_no_puede_cambiar_la_gestion(as_auditor, db_session):
    ing = _caso(db_session)
    oda = _oda(db_session, ing, "4004", _d(-40), _d(-20))
    db_session.commit()
    r = as_auditor.patch(f"/api/v1/odas/{oda.id}/gestion", json={"estado_gestion": "recibida"})
    assert r.status_code == 403


def test_gestion_de_oda_inexistente_da_404(as_coordinacion):
    r = as_coordinacion.patch("/api/v1/odas/999999/gestion", json={"estado_gestion": "recibida"})
    assert r.status_code == 404


def test_misma_gestion_no_deja_traza(as_coordinacion, db_session):
    ing = _caso(db_session)
    oda = _oda(db_session, ing, "4005", _d(-40), _d(-20))
    db_session.commit()
    r = as_coordinacion.patch(f"/api/v1/odas/{oda.id}/gestion", json={"estado_gestion": "pendiente"})
    assert r.status_code == 200
    assert not db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "oda", AuditLog.entity_id == str(oda.id))
    ).all()


# ── Excel ──────────────────────────────────────────────────────────────────────


def test_excel_reproduce_la_tabla_y_respeta_el_filtro(as_coordinacion, db_session):
    a = _caso(db_session, nombre="Excel Ley Karin", rut="12345678-5", programa="Ley Karin")
    _oda(db_session, a, "5001", _d(-60), _d(-30), tipo="Ambulatoria", vigente=False)
    _oda(db_session, a, "5002", _d(-35), _d(-20), tipo="OPA")
    _cita(db_session, a, _d(-25))
    _cita(db_session, a, _d(-33))
    b = _caso(db_session, nombre="Excel PIPT", programa="PIPT")
    _oda(db_session, b, "5003", _d(-40), _d(-20))
    db_session.commit()

    r = as_coordinacion.get("/api/v1/reportes/odas-vencidas/excel", params={"programa": "ley_karin"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "odas-vencidas" in r.headers["content-disposition"]
    filas = list(load_workbook(io.BytesIO(r.content)).active.iter_rows(values_only=True))
    assert filas[0] == (
        "Folio", "Nombre", "RUT", "Programa", "Región", "Comuna", "Fecha de atención",
        "N° ODA/OPA", "Tipo", "Fecha inicio", "Fecha término", "Cobertura", "Estado de gestión",
    )
    # QA-006: una fila por fecha de atención, cada una con la orden que la cubre.
    assert len(filas) == 3
    por_fecha = {f[6].date(): f for f in filas[1:]}
    temprana, tardia = por_fecha[_d(-33)], por_fecha[_d(-25)]
    assert temprana[:6] == (a.folio, "Excel Ley Karin", "12345678-5", "Ley Karin", "Maule", "—")
    # El -33 lo cubren las dos órdenes; el -25, solo la 5002.
    assert temprana[7:9] == ("5001 / 5002", "ODA / OPA")
    assert tardia[7:11] == ("5002", "OPA", f"{_d(-35):%d-%m-%Y}", f"{_d(-20):%d-%m-%Y}")
    assert (tardia[11], tardia[12]) == ("CUBRE", "Pendiente")


def test_excel_celdas_sin_dato_llevan_guion(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Excel antiguo")
    _oda(db_session, ing, "5004", None, _d(-20), tipo=None)
    db_session.commit()
    r = as_coordinacion.get("/api/v1/reportes/odas-vencidas/excel")
    filas = list(load_workbook(io.BytesIO(r.content)).active.iter_rows(values_only=True))
    fila = next(f for f in filas if f[1] == "Excel antiguo")
    assert (fila[6], fila[8], fila[9]) == ("—", "—", "—")


# ── QA-006: listado por paciente ───────────────────────────────────────────────


def _estado(cliente, **params):
    r = cliente.get("/api/v1/reportes/odas-estado", params=params)
    assert r.status_code == 200, r.text
    return {i["paciente_nombre"]: i for i in r.json()["items"]}


def test_listado_por_paciente_con_estado_de_caso_y_de_oda(as_coordinacion, db_session):
    casos = {
        "L Vigente": (_d(30), "activo"),
        "L PorVencer": (_d(9), "activo"),
        "L Vencida": (_d(-3), "activo"),
        "L Cerrado": (_d(40), "cerrado"),
        "L Encuadre": (_d(-10), "encuadre"),
    }
    for nombre, (fin, estado) in casos.items():
        ing = _caso(db_session, nombre=nombre, estado=estado, fecha_ingreso=date(2026, 3, 2))
        _oda(db_session, ing, f"6{_n}", fin - timedelta(days=20), fin)
    _caso(db_session, nombre="L SinOda")
    db_session.commit()

    items = _estado(as_coordinacion)
    assert items["L Vigente"]["estado_oda"] == "vigente"
    assert items["L Vigente"]["dias_para_vencer"] == 30
    assert items["L PorVencer"]["estado_oda"] == "por_vencer"
    assert items["L PorVencer"]["dias_para_vencer"] == 9
    assert items["L Vencida"]["estado_oda"] == "vencida"
    assert items["L Vencida"]["dias_para_vencer"] == -3
    assert items["L Cerrado"]["estado_caso"] == "cerrado"
    assert items["L Encuadre"]["estado_caso"] == "encuadre"
    assert items["L SinOda"]["estado_oda"] == "sin_oda"
    assert items["L SinOda"]["dias_para_vencer"] is None
    assert items["L Vigente"]["fecha_ingreso"] == "2026-03-02"
    assert items["L Vigente"]["paciente_rut"]


def test_listado_filtra_por_estado_de_caso(as_coordinacion, db_session):
    _caso(db_session, nombre="F Activo", estado="activo")
    _caso(db_session, nombre="F Cerrado", estado="cerrado")
    db_session.commit()
    assert set(_estado(as_coordinacion, estado_caso="cerrado")) == {"F Cerrado"}


def test_listado_el_auditor_puede_leer(as_auditor):
    assert as_auditor.get("/api/v1/reportes/odas-estado").status_code == 200


# ── Licencias: folio real ──────────────────────────────────────────────────────


def test_licencias_trae_el_folio_real_y_el_rut(as_coordinacion, db_session):
    from app.models.licencia import LicenciaMedica

    ing = _caso(db_session, nombre="Lic folio", rut="22222222-2")
    db_session.add(
        LicenciaMedica(
            ingreso_id=ing.id, folio_lm="LM-9", tipo_lm="1", tipo_reposo="total",
            cantidad_dias=5, origen="sistema", fecha_inicio=date(2026, 2, 1),
            fecha_termino=date(2026, 2, 5), fecha_emision=date(2026, 2, 1),
            inicio_reposo=date(2026, 2, 1), fin_reposo=date(2026, 2, 5), diagnostico="t",
        )
    )
    db_session.commit()
    r = as_coordinacion.get(
        "/api/v1/reportes/licencias",
        params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"},
    )
    item = next(i for i in r.json()["items"] if i["folio_id"] == ing.id)
    assert item["folio"] == ing.folio
    assert item["rut_paciente"] == "22222222-2"


# ── Migración 1470 y compatibilidad con Oracle ─────────────────────────────────


def test_migracion_1470_agrega_columnas_a_oda():
    from sqlalchemy import inspect

    from app.db.session import engine

    cols = {c["name"]: c for c in inspect(engine).get_columns("oda")}
    assert cols["tipo_orden"]["nullable"] is True
    assert cols["estado_gestion"]["nullable"] is False


def test_migracion_1470_sube_y_baja_en_una_bd_propia():
    """Sube a 1470, baja a 1460 y vuelve a subir sobre una BD descartable."""
    import os

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.engine import make_url

    # En CI solo existe DATABASE_URL; en local puede venir TEST_DATABASE_URL (conftest la copia).
    url = make_url(os.environ["DATABASE_URL"])
    if url.get_backend_name() != "postgresql":
        pytest.skip("Crea una BD descartable con SQL de PostgreSQL; Oracle lo cubre el smoke de CI.")
    nombre = f"{url.database}_mig1470"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{nombre}"'))
        c.execute(text(f'CREATE DATABASE "{nombre}"'))
    destino = url.set(database=nombre)
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", destino.render_as_string(hide_password=False))
    try:
        command.upgrade(cfg, "1470")
        eng = create_engine(destino)
        assert {"tipo_orden", "estado_gestion"} <= {c["name"] for c in inspect(eng).get_columns("oda")}
        command.downgrade(cfg, "1460")
        assert not {"tipo_orden", "estado_gestion"} & {c["name"] for c in inspect(eng).get_columns("oda")}
        command.upgrade(cfg, "1470")
        eng.dispose()
    finally:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)'))


def test_las_consultas_nuevas_compilan_para_oracle():
    from sqlalchemy.dialects import oracle

    from app.services import reporte_odas as svc

    stmt = svc.aplicar_programa(select(Ingreso.id), "ley_karin")
    sql = str(stmt.compile(dialect=oracle.dialect())).lower()
    assert "lower(ingreso.programa) like" in sql
    assert " is 1" not in sql




def test_excel_neutraliza_formulas_en_el_texto(as_coordinacion, db_session):
    ing = _caso(db_session, nombre='=HYPERLINK("http://x","clic")')
    _oda(db_session, ing, "+1234", _d(-40), _d(-20))
    db_session.commit()
    r = as_coordinacion.get("/api/v1/reportes/odas-vencidas/excel")
    filas = list(load_workbook(io.BytesIO(r.content)).active.iter_rows(values_only=True))
    fila = next(f for f in filas if "HYPERLINK" in str(f[1]))
    assert fila[1].startswith("'=")
    assert fila[7] == "'+1234"


def test_consultas_por_lotes_con_mas_de_un_lote(as_coordinacion, db_session, monkeypatch):
    """Oracle rechaza >1000 valores en un IN: con lote de 2 y 5 pacientes hay 3 lotes."""
    from app.agendamiento import salutem

    monkeypatch.setattr(salutem, "_LOTE", 2)
    for k in range(5):
        ing = _caso(db_session, nombre=f"Lote {k}")
        _oda(db_session, ing, f"7{_n}", _d(-40), _d(-20))
        _cita(db_session, ing, _d(-30))
        _cita(db_session, ing, _d(-5))
    db_session.commit()
    r = as_coordinacion.get("/api/v1/reportes/odas-vencidas")
    filas = [i for i in r.json()["items"] if i["paciente_nombre"].startswith("Lote ")]
    assert len(filas) == 5
    for f in filas:
        assert f["cobertura"] == "SOLICITAR"
        assert len(f["fechas_atencion"]) == 2
        assert len(f["ordenes"]) == 1


# ── Atendidos sin ODA (18-11): también se solicita ─────────────────────────────


def _sin_oda(cliente, **params):
    r = cliente.get("/api/v1/reportes/odas-vencidas", params=params)
    assert r.status_code == 200, r.text
    return r.json()["items"]


def test_atendido_sin_oda_aparece_como_solicitar(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Atendido sin orden")
    _cita(db_session, ing, _d(-10))
    _cita(db_session, ing, _d(-3))
    _cita(db_session, ing, _d(-2), estado="agendada")  # no cuenta
    db_session.commit()
    f = _fila(as_coordinacion, "Atendido sin orden")
    assert f["cobertura"] == "SOLICITAR"
    assert f["fechas_atencion"] == [_d(-10).isoformat(), _d(-3).isoformat()]
    assert f["ordenes"] == []
    assert f["identificador"] is None
    assert f["fecha_registro"] is None and f["fecha_vencimiento"] is None
    assert f["estado_gestion"] is None
    assert f["id"] is None
    assert f["folio"] == ing.folio


def test_sin_oda_requiere_cita_realizada_e_ingreso_activo(as_coordinacion, db_session):
    solo_agendada = _caso(db_session, nombre="Solo agendada")
    _cita(db_session, solo_agendada, _d(5), estado="agendada")
    sin_citas = _caso(db_session, nombre="Sin citas")
    cerrado = _caso(db_session, nombre="Cerrado atendido", estado="cerrado")
    _cita(db_session, cerrado, _d(-5))
    db_session.commit()
    nombres = {i["paciente_nombre"] for i in _sin_oda(as_coordinacion)}
    assert not nombres & {"Solo agendada", "Sin citas", "Cerrado atendido"}
    assert sin_citas.id  # creado, pero sin atenciones


def test_paciente_con_oda_vigente_no_aparece_como_sin_oda(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Con orden vigente")
    _oda(db_session, ing, "5001", _d(-5), _d(30))
    _cita(db_session, ing, _d(-2))
    db_session.commit()
    nombres = [i["paciente_nombre"] for i in _sin_oda(as_coordinacion)]
    assert "Con orden vigente" not in nombres


def test_orden_en_otro_ingreso_del_paciente_cuenta_como_registrada(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Dos ingresos")
    _cita(db_session, ing, _d(-4))
    otro = Ingreso(
        paciente_id=ing.paciente_id, folio="F-QA-OTRO", folio_manual=True, programa="PIPT",
        fecha_ingreso=date(2025, 6, 1), tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="t", estado="cerrado",
    )
    db_session.add(otro)
    db_session.flush()
    _oda(db_session, otro, "6001", _d(-300), _d(-250))
    db_session.commit()
    nombres = [i["paciente_nombre"] for i in _sin_oda(as_coordinacion)]
    assert "Dos ingresos" not in nombres


def test_paciente_con_oda_vencida_no_se_duplica(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Vencida y atendida")
    _oda(db_session, ing, "7001", _d(-40), _d(-20))
    _cita(db_session, ing, _d(-30))
    db_session.commit()
    items = [i for i in _sin_oda(as_coordinacion) if i["paciente_nombre"] == "Vencida y atendida"]
    assert len(items) == 1
    assert items[0]["identificador"] == "7001"


def test_sin_oda_respeta_filtros_de_programa_region_y_comuna(as_coordinacion, db_session):
    a = _caso(db_session, nombre="Regular Talca", programa="Programa Regular")
    b = _caso(db_session, nombre="PIPT Linares", programa="PIPT")
    pa = db_session.get(Paciente, a.paciente_id)
    pb = db_session.get(Paciente, b.paciente_id)
    pa.comuna, pb.comuna = "Talca", "Linares"
    pb.region = "Otra"
    _cita(db_session, a, _d(-3))
    _cita(db_session, b, _d(-3))
    db_session.commit()

    def nombres(**p):
        return {i["paciente_nombre"] for i in _sin_oda(as_coordinacion, **p)}

    assert {"Regular Talca", "PIPT Linares"} <= nombres()
    n = nombres(programa="pipt")
    assert "PIPT Linares" in n and "Regular Talca" not in n
    n = nombres(region="Maule")
    assert "Regular Talca" in n and "PIPT Linares" not in n
    n = nombres(comuna="Linares")
    assert "PIPT Linares" in n and "Regular Talca" not in n


def test_excel_incluye_atendidos_sin_oda(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Excel sin orden")
    _cita(db_session, ing, date(2026, 11, 2))
    db_session.commit()
    r = as_coordinacion.get("/api/v1/reportes/odas-vencidas/excel")
    assert r.status_code == 200
    ws = load_workbook(io.BytesIO(r.content)).active
    fila = next(row for row in ws.iter_rows(values_only=True) if row[1] == "Excel sin orden")
    assert fila[7:11] == ("—", "—", "—", "—")
    assert fila[6].date() == date(2026, 11, 2)
    assert ws["G2"].number_format == "DD-MM-YYYY"
    assert fila[11] == "SOLICITAR"
    assert fila[12] == "—"
