"""Reporte «Externalizado» de fármacos (QA-010 / QA-013): catálogos sembrados por la migración
1550 y el reporte por período con su clasificación. Datos de pacientes inventados.
"""

import io
from datetime import date, datetime, timezone

from openpyxl import load_workbook
from sqlalchemy import func, select

from app.models.farmaco_convenio import FarmacoCanasta, FarmacoExternalizado
from app.models.farmacos import EsquemaIndicacion, Receta, RegistroFarmacologico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente

URL = "/api/v1/reportes/farmacos-convenio"
PERIODO = {"fecha_desde": "2031-05-01", "fecha_hasta": "2031-05-31"}
_n = 0


def _registro(db, nombre: str) -> RegistroFarmacologico:
    global _n
    _n += 1
    p = Paciente(rut=f"{21_000_000 + _n}-2", nombre=nombre, sexo="M", edad=50, region="Maule")
    db.add(p)
    db.flush()
    ing = Ingreso(
        paciente_id=p.id, folio=f"F-FAR-{_n}", folio_manual=True, programa="Programa Regular",
        fecha_ingreso=date(2031, 1, 5), tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="t", estado="activo",
    )
    db.add(ing)
    db.flush()
    reg = RegistroFarmacologico(ingreso_id=ing.id, medico_tratante="Dra. Prueba", estado_farmacologico="activo")
    db.add(reg)
    db.flush()
    return reg


def _receta(db, reg, marca: str, emision: date) -> None:
    db.add(Receta(registro_id=reg.id, fecha_emision=emision, fecha_revision=emision, marca_medicamento=marca))
    db.flush()


def _items(cliente, nombre: str, **params):
    r = cliente.get(URL, params={**PERIODO, **params})
    assert r.status_code == 200, r.text
    return [i for i in r.json()["items"] if i["paciente_nombre"] == nombre]


def test_la_migracion_siembra_los_dos_catalogos(db_session):
    assert db_session.scalar(select(func.count()).select_from(FarmacoCanasta)) == 206
    assert db_session.scalar(select(func.count()).select_from(FarmacoExternalizado)) == 51
    alprazolam = db_session.scalar(select(FarmacoCanasta).where(FarmacoCanasta.codigo_sap == "3073"))
    assert alprazolam.descripcion == "ALPRAZOLAM 0.5MG. CAJA 30 COMP."
    assert alprazolam.principio_activo == "ALPRAZOLAM"
    solo_001 = db_session.scalars(
        select(FarmacoExternalizado.glosa).where(FarmacoExternalizado.convenio_001 == True)  # noqa: E712
    ).all()
    assert sorted(solo_001) == ["CIRCALIFE MELATONINA 3MG", "MELATONINA 3 MG 60 CAPS"]


def test_recetas_del_periodo_con_su_clasificacion(as_coordinacion, db_session):
    reg = _registro(db_session, "Far Recetas")
    _receta(db_session, reg, "Alprazolam 0,5 mg", date(2031, 5, 3))
    _receta(db_session, reg, "Circalife melatonina 3mg", date(2031, 5, 4))
    _receta(db_session, reg, "Melatonina 3 mg", date(2031, 5, 5))
    _receta(db_session, reg, "Paracetamol 500 mg", date(2031, 5, 6))
    _receta(db_session, reg, "Deprax 50 mg", date(2031, 6, 1))  # fuera del período
    db_session.commit()
    items = _items(as_coordinacion, "Far Recetas")
    assert [(i["farmaco"], i["clasificacion"]) for i in items] == [
        ("Alprazolam 0,5 mg", "Convenio 002"),
        ("Circalife melatonina 3mg", "Convenio 001"),
        ("Melatonina 3 mg", "REVISAR"),
        ("Paracetamol 500 mg", "Fuera de convenio"),
    ]
    primero = items[0]
    assert primero["codigo_sap"] == "3073"
    assert primero["origen"] == "Receta"
    assert primero["folio"].startswith("F-FAR-")
    assert primero["paciente_rut"]


def test_incluye_los_medicamentos_del_esquema(as_coordinacion, db_session):
    reg = _registro(db_session, "Far Esquema")
    db_session.add(
        EsquemaIndicacion(
            registro_id=reg.id, medicamento="Sertralina 50 mg", dosis="1 comp", frecuencia="cada 24 h",
            created_at=datetime(2031, 5, 10, 15, 0, tzinfo=timezone.utc),
        )
    )
    db_session.commit()
    [item] = _items(as_coordinacion, "Far Esquema")
    assert (item["origen"], item["fecha"], item["clasificacion"]) == ("Esquema", "2031-05-10", "Convenio 002")
    assert item["dosis"] == "1 comp / cada 24 h"


def test_filtro_por_paciente_y_resumen(as_coordinacion, db_session):
    a = _registro(db_session, "Far Uno")
    b = _registro(db_session, "Far Dos")
    _receta(db_session, a, "Deprax 100 mg caja 30", date(2031, 5, 7))
    _receta(db_session, b, "Paracetamol", date(2031, 5, 7))
    db_session.commit()
    pid = db_session.get(Ingreso, a.ingreso_id).paciente_id
    r = as_coordinacion.get(URL, params={**PERIODO, "paciente_id": pid})
    assert r.status_code == 200
    body = r.json()
    assert {i["paciente_nombre"] for i in body["items"]} == {"Far Uno"}
    resumen = {x["clasificacion"]: x["total"] for x in body["resumen"]}
    assert resumen == {"Convenio 002": 1, "Convenio 001": 0, "REVISAR": 0, "Fuera de convenio": 0}


def test_solo_coordinacion_y_administrativo(as_admin, as_auditor):
    assert as_admin.get(URL, params=PERIODO).status_code == 200
    assert as_auditor.get(URL, params=PERIODO).status_code == 403
    assert as_auditor.get(f"{URL}/excel", params=PERIODO).status_code == 403


def test_fechas_obligatorias_y_rango_valido(as_coordinacion):
    assert as_coordinacion.get(URL).status_code == 422
    r = as_coordinacion.get(URL, params={"fecha_desde": "2031-05-31", "fecha_hasta": "2031-05-01"})
    assert r.status_code == 422


def test_excel(as_admin, db_session):
    reg = _registro(db_session, "Far Excel")
    _receta(db_session, reg, "Bupropión 300 mg", date(2031, 5, 8))
    db_session.commit()
    r = as_admin.get(f"{URL}/excel", params=PERIODO)
    assert r.status_code == 200
    assert "externalizado-2031-05-01-2031-05-31.xlsx" in r.headers["content-disposition"]
    ws = load_workbook(io.BytesIO(r.content)).active
    encabezados = [c.value for c in ws[1]]
    assert encabezados[:4] == ["Fecha", "Paciente", "RUT", "Folio"]
    fila = next([c.value for c in f] for f in ws.iter_rows(min_row=2) if f[1].value == "Far Excel")
    datos = dict(zip(encabezados, fila))
    assert datos["Clasificación"] == "REVISAR"
    assert "principio activo" in datos["Detalle"]
    assert datos["Código SAP"] == "—"
