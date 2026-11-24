"""Reporte «Ambulatorio» en formato de la plataforma ISL (QA del 23-11-2026).

Una fila por atención realizada con región, código región, comuna, código comuna (CUT), la
orden ODA/OPA de SIGE que cubre la fecha, la prestación de la cita de SALUTEM, la hora y el
folio. Datos de prueba inventados.
"""

import io
from datetime import date, datetime, timezone

from openpyxl import load_workbook

from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemCita

URL = "/api/v1/reportes/ambulatorio"
DESDE, HASTA = date(2031, 3, 1), date(2031, 3, 31)
PERIODO = {"fecha_desde": DESDE.isoformat(), "fecha_hasta": HASTA.isoformat()}
AHORA = datetime(2031, 3, 1, tzinfo=timezone.utc)
_n = 0


def _sig() -> int:
    global _n
    _n += 1
    return _n


def _caso(db, *, nombre, region="Maule", comuna=None, programa="Programa Regular",
          especialidad=None) -> Ingreso:
    n = _sig()
    p = Paciente(rut=f"{20_000_000 + n}-5", nombre=nombre, sexo="F", edad=35, region=region, comuna=comuna)
    db.add(p)
    db.flush()
    ing = Ingreso(
        paciente_id=p.id, folio=f"F-AMB-{n}", folio_manual=True, programa=programa,
        fecha_ingreso=date(2031, 1, 5), tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="t", estado="activo", especialidad=especialidad,
    )
    db.add(ing)
    db.flush()
    return ing


def _cita(db, ing, fecha, *, estado="realizada", especialidad=None, salutem=None) -> Cita:
    sid = None
    if salutem is not None:
        sid = 8_800_000 + _sig()
        db.add(
            SalutemCita(
                cita_id=sid, persona_id=1, fecha_cita=fecha, contenido=salutem, hash_contenido="h",
                visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
            )
        )
    c = Cita(ingreso_id=ing.id, estado=estado, fecha=fecha, especialidad=especialidad,
             salutem_cita_id=sid, origen="SALUTEM" if sid else "SIGE")
    db.add(c)
    db.flush()
    return c


def _oda(db, ing, ident, inicio, fin, tipo) -> None:
    db.add(Oda(ingreso_id=ing.id, identificador=ident, fecha_registro=inicio,
               fecha_vencimiento=fin, vigente=True, tipo_orden=tipo))
    db.flush()


def _filas(cliente, nombre, **params):
    r = cliente.get(URL, params={**PERIODO, **params})
    assert r.status_code == 200, r.text
    return [i for i in r.json()["items"] if i["nombre"] == nombre]


def test_codigos_cut_desde_la_comuna(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Talca", region="Maule", comuna="talca")
    _cita(db_session, ing, date(2031, 3, 10))
    db_session.commit()
    [f] = _filas(as_coordinacion, "Amb Talca")
    assert (f["region"], f["codigo_region"], f["comuna"], f["codigo_comuna"]) == (
        "Maule", "07", "Talca", "07101"
    )
    assert f["cantidad"] == 1
    assert f["folio"] == ing.folio
    assert f["programa"] == "Programa Regular"
    assert f["numero_cuenta"] is None and f["monto_total"] is None


def test_codigo_region_desde_la_region_si_la_comuna_no_se_conoce(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Sin Comuna", region="Magallanes", comuna="Villa Inventada")
    _cita(db_session, ing, date(2031, 3, 11))
    db_session.commit()
    [f] = _filas(as_coordinacion, "Amb Sin Comuna")
    assert (f["region"], f["codigo_region"], f["comuna"], f["codigo_comuna"]) == (
        "Magallanes", "12", "Villa Inventada", None
    )


def test_una_fila_por_atencion_realizada_dentro_del_periodo(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Varias")
    _cita(db_session, ing, date(2031, 3, 2))
    _cita(db_session, ing, date(2031, 3, 20))
    _cita(db_session, ing, date(2031, 3, 21), estado="inasistencia")
    _cita(db_session, ing, date(2031, 3, 22), estado="agendada")
    _cita(db_session, ing, date(2031, 4, 2))  # fuera del período
    db_session.commit()
    filas = _filas(as_coordinacion, "Amb Varias")
    assert [f["fecha"] for f in filas] == ["2031-03-02", "2031-03-20"]


def test_oda_y_opa_en_su_columna_segun_la_orden_que_cubre_la_fecha(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Ordenes")
    _oda(db_session, ing, "5550001", date(2031, 3, 1), date(2031, 3, 15), "Ambulatoria")
    _oda(db_session, ing, "5550002", date(2031, 3, 16), date(2031, 3, 31), "OPAEP")
    _cita(db_session, ing, date(2031, 3, 5))
    _cita(db_session, ing, date(2031, 3, 25))
    db_session.commit()
    a, b = _filas(as_coordinacion, "Amb Ordenes")
    assert (a["oda"], a["opa"]) == ("5550001", None)
    assert (b["oda"], b["opa"]) == (None, "5550002")


def test_sin_orden_que_cubra_quedan_vacias(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Sin Orden")
    _oda(db_session, ing, "5550003", date(2031, 1, 1), date(2031, 1, 31), "Ambulatoria")
    _cita(db_session, ing, date(2031, 3, 5))
    db_session.commit()
    [f] = _filas(as_coordinacion, "Amb Sin Orden")
    assert (f["oda"], f["opa"]) == (None, None)


def test_prestacion_y_hora_desde_la_cita_de_salutem(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Salutem")
    _cita(
        db_session, ing, date(2031, 3, 6), especialidad="Psicología",
        salutem={
            "citaHoraInicio": "09:30:00",
            "prestaciones": [
                {"id": 1, "codigo": "3", "nombre": "Consulta psicológica tratamiento"},
                {"id": 2, "codigo": "14", "nombre": "Gestión Administrativa"},
            ],
        },
    )
    db_session.commit()
    [f] = _filas(as_coordinacion, "Amb Salutem")
    assert f["codigo_prestacion"] == "3 / 14"
    assert f["glosa_prestacion"] == "Consulta psicológica tratamiento / Gestión Administrativa"
    assert f["hora"] == "09:30"


def test_hora_desde_la_atencion_si_la_cita_no_la_trae(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Atencion")
    c = _cita(db_session, ing, date(2031, 3, 7), especialidad="Médico/a", salutem={})
    db_session.add(
        SalutemAtencion(
            cita_id=c.salutem_cita_id, persona_id=1, fecha_cita=c.fecha,
            contenido={"citaHorarioInicio": "16:00:00"}, hash_contenido="h",
            visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
        )
    )
    db_session.commit()
    [f] = _filas(as_coordinacion, "Amb Atencion")
    assert f["hora"] == "16:00"
    # Sin prestaciones en SALUTEM: la glosa es la especialidad de la cita.
    assert (f["codigo_prestacion"], f["glosa_prestacion"]) == (None, "Médico/a")


def test_sin_salutem_la_glosa_es_la_especialidad_del_ingreso(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Especialidad", especialidad="Psiquiatría")
    _cita(db_session, ing, date(2031, 3, 8))
    db_session.commit()
    [f] = _filas(as_coordinacion, "Amb Especialidad")
    assert (f["codigo_prestacion"], f["glosa_prestacion"], f["hora"]) == (None, "Psiquiatría", None)


def test_filtros_por_programa_y_region(as_coordinacion, db_session):
    a = _caso(db_session, nombre="Amb Karin", programa="Ley Karin", region="Maule")
    b = _caso(db_session, nombre="Amb Regular Biobio", region="Biobío")
    _cita(db_session, a, date(2031, 3, 9))
    _cita(db_session, b, date(2031, 3, 9))
    db_session.commit()
    assert len(_filas(as_coordinacion, "Amb Karin", programa="ley_karin")) == 1
    assert _filas(as_coordinacion, "Amb Regular Biobio", programa="ley_karin") == []
    assert len(_filas(as_coordinacion, "Amb Regular Biobio", region="Biobío")) == 1
    assert _filas(as_coordinacion, "Amb Karin", region="Biobío") == []


def test_fechas_obligatorias_y_rango_valido(as_coordinacion):
    assert as_coordinacion.get(URL).status_code == 422
    r = as_coordinacion.get(URL, params={"fecha_desde": "2031-03-31", "fecha_hasta": "2031-03-01"})
    assert r.status_code == 422


def test_lectores_como_los_reportes_de_oda(as_auditor, as_admin, client):
    assert as_auditor.get(URL, params=PERIODO).status_code == 200
    assert as_admin.get(URL, params=PERIODO).status_code == 200
    assert client.get(URL, params=PERIODO).status_code == 401


def test_excel_con_el_formato_de_la_plataforma_isl(as_coordinacion, db_session):
    ing = _caso(db_session, nombre="Amb Excel", region="Los Ríos", comuna="Valdivia")
    _oda(db_session, ing, "5550009", date(2031, 3, 1), date(2031, 3, 31), "Ambulatoria")
    _cita(db_session, ing, date(2031, 3, 12), salutem={
        "citaHoraInicio": "10:00:00", "prestaciones": [{"id": 9, "codigo": "6", "nombre": "Control médico"}],
    })
    db_session.commit()
    r = as_coordinacion.get(f"{URL}/excel", params=PERIODO)
    assert r.status_code == 200
    assert "ambulatorio-2031-03-01-2031-03-31.xlsx" in r.headers["content-disposition"]
    ws = load_workbook(io.BytesIO(r.content)).active
    encabezados = [c.value for c in ws[1]]
    assert encabezados[:4] == ["Región", "Código región", "Comuna", "Código comuna"]
    assert encabezados[-2:] == ["Folio", "Programa"]
    fila = next(
        [c.value for c in f] for f in ws.iter_rows(min_row=2) if f[8].value == "Amb Excel"
    )
    datos = dict(zip(encabezados, fila))
    # Códigos como número, igual que la planilla del ISL (14 y 14101).
    assert (datos["Región"], datos["Código región"], datos["Comuna"], datos["Código comuna"]) == (
        "Los Ríos", 14, "Valdivia", 14101
    )
    assert datos["ODA"] == "5550009" and datos["OPA"] == "—"
    assert datos["Código prestación"] == "6" and datos["Hora"] == "10:00"
    assert datos["Cantidad"] == 1 and datos["Monto total"] == "—"
    assert datos["Folio"] == ing.folio
