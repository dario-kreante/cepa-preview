"""Carga del «Reporte Prestador» del portal ISL (QA-004, QA UTalca 22-10).

El fixture `fixtures/reporte_prestador_isl.xlsx` replica el formato del archivo real
(hoja «Reporte Prestador», fechas como texto dd-mm-aaaa, «Rut Trabajador» casi siempre
vacío) con datos ficticios.
"""

import io
from datetime import date, timedelta
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums_alertas import TipoAlerta
from app.models.alertas import AlertaNotif
from app.models.audit_log import AuditLog
from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.services.alertas import _construir_hitos_oda, ejecutar_job_alertas
from app.services.oda_importacion import ArchivoInvalidoError, importar_reporte, parsear_reporte

FIXTURE = Path(__file__).parent / "fixtures" / "reporte_prestador_isl.xlsx"
HOY = date.today()
URL = "/api/v1/odas/importar"

ENCABEZADO = [
    "N° de Orden", "Tipo de Orden", "Inicio Vigencia", "Fin Vigencia", "Días", "Fecha Cese",
    "Estado Orden", "N° Siniestro", "CUN del Siniestro", "Rut Trabajador", "Rut Prestador",
    "Nombre Prestador", "Agencia", "Región", "Fecha Creación",
]


def _f(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def _fila(orden, siniestro, fin, *, inicio=None, estado="VIGENTE", cese="", rut=None, tipo="OPA"):
    inicio = inicio or (fin - timedelta(days=6))
    return [
        orden, tipo, _f(inicio), _f(fin), 7, _f(cese) if cese else "", estado, siniestro,
        "9999999", rut, "700000001", "PRESTADOR", "AGENCIA", "Región del Maule", _f(inicio),
    ]


def _xlsx(filas, *, encabezado=ENCABEZADO, titulos=(), hoja="Reporte Prestador") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    for t in titulos:
        ws.append([t])
    ws.append(encabezado)
    for f in filas:
        ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_n = 0


def _ingreso(db: Session, *, siniestro=None, rut=None, estado="activo", fecha=date(2026, 1, 1)) -> Ingreso:
    global _n
    _n += 1
    p = Paciente(rut=rut, nombre=f"Paciente {_n}", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    i = Ingreso(
        paciente_id=p.id, folio=f"F-IMP-{_n}", folio_manual=True, fecha_ingreso=fecha,
        numero_siniestro=siniestro, tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="test", estado=estado,
    )
    db.add(i)
    db.flush()
    return i


def _subir(cliente, contenido: bytes, *, dry_run=False, nombre="reporte.xlsx"):
    return cliente.post(
        URL,
        params={"dry_run": str(dry_run).lower()},
        files={"file": (nombre, contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def _odas(db: Session, ingreso_id: int) -> list[Oda]:
    return list(db.scalars(select(Oda).where(Oda.ingreso_id == ingreso_id).order_by(Oda.id)))


# ── Parser ─────────────────────────────────────────────────────────────────────


def test_parser_lee_el_fixture_con_formato_real():
    r = parsear_reporte(FIXTURE.read_bytes())
    assert r.filas_leidas == 10
    assert r.errores == []
    assert [f.fila for f in r.filas] == list(range(2, 12))
    primera = r.filas[0]
    assert primera.numero_orden == "900001"
    assert primera.tipo_orden == "OPAEP"
    assert primera.inicio == date(2025, 12, 28)
    assert primera.fin == date(2026, 1, 3)
    assert primera.siniestro == "1000001"
    assert primera.estado == "VENCIDA"
    assert primera.rut_trabajador is None
    assert {f.tipo_orden for f in r.filas} == {"OPAEP", "Ambulatoria", "OPA"}


def test_parser_usa_fecha_cese_solo_si_es_anterior_al_fin():
    filas = {f.numero_orden: f for f in parsear_reporte(FIXTURE.read_bytes()).filas}
    assert filas["900002"].fecha_vencimiento == date(2026, 2, 26)  # cese antes del fin
    assert filas["900003"].fecha_vencimiento == date(2026, 1, 23)  # cese después: manda el fin


def test_parser_encuentra_el_encabezado_bajo_filas_de_titulo_y_salta_filas_vacias():
    fin = HOY + timedelta(days=10)
    contenido = _xlsx(
        [_fila(1, "S1", fin), [None] * 15, _fila(2, "S2", fin)],
        titulos=["Reporte Prestador ISL", "Generado el 22-10-2026"],
        hoja="Otra hoja",
    )
    r = parsear_reporte(contenido)
    assert [f.numero_orden for f in r.filas] == ["1", "2"]
    assert r.filas_leidas == 2


def test_parser_reporta_errores_por_fila():
    fin = HOY + timedelta(days=10)
    malas = _fila(2, "S2", fin)
    malas[3] = "31-02-2026"
    sin_orden = _fila(None, "S3", fin)
    r = parsear_reporte(_xlsx([_fila(1, "S1", fin), malas, sin_orden]))
    assert len(r.filas) == 1
    assert [(e.fila, "fecha inválida" in e.motivo or "Sin N°" in e.motivo) for e in r.errores] == [
        (3, True), (4, True),
    ]


def test_parser_rechaza_archivo_sin_columnas_obligatorias():
    with pytest.raises(ArchivoInvalidoError, match="N° Siniestro"):
        parsear_reporte(_xlsx([], encabezado=[c for c in ENCABEZADO if c != "N° Siniestro"]))
    with pytest.raises(ArchivoInvalidoError):
        parsear_reporte(b"esto no es un excel")


def test_parser_rechaza_planillas_desmedidas(monkeypatch: pytest.MonkeyPatch):
    import app.services.oda_importacion as mod

    fin = HOY + timedelta(days=10)
    contenido = _xlsx([_fila(i, f"S{i}", fin) for i in range(1, 4)])
    monkeypatch.setattr(mod, "MAX_FILAS", 2)
    with pytest.raises(ArchivoInvalidoError, match="máximo de 2 filas"):
        parsear_reporte(contenido)
    monkeypatch.setattr(mod, "MAX_DESCOMPRIMIDO_BYTES", 10)
    with pytest.raises(ArchivoInvalidoError, match="demasiado grande"):
        parsear_reporte(contenido)


# ── Servicio: match, upsert y vigencia ─────────────────────────────────────────


def test_match_por_siniestro_y_respaldo_por_rut(db_session: Session):
    por_siniestro = _ingreso(db_session, siniestro="1000001")
    por_rut = _ingreso(db_session, siniestro="OTRO", rut="123456785")
    r = importar_reporte(db_session, FIXTURE.read_bytes(), hoy=date(2026, 10, 29))

    assert r.match_por_siniestro == 2  # órdenes 900001 y 900009, mismo siniestro
    assert r.match_por_rut == 1  # 900008: siniestro sin ingreso, RUT 12.345.678-5 sí
    assert {o.identificador for o in _odas(db_session, por_siniestro.id)} == {"900001", "900009"}
    assert [o.identificador for o in _odas(db_session, por_rut.id)] == ["900008"]
    assert len(r.sin_paciente) == 7
    assert {s.numero_orden for s in r.sin_paciente} >= {"900002", "900005", "900006"}


def test_siniestro_con_ceros_a_la_izquierda_calza(db_session: Session):
    ing = _ingreso(db_session, siniestro=" 0001000004 ")
    importar_reporte(db_session, FIXTURE.read_bytes())
    assert [o.identificador for o in _odas(db_session, ing.id)] == ["900004"]


def test_varios_ingresos_con_el_mismo_siniestro_prefiere_el_activo(db_session: Session):
    _ingreso(db_session, siniestro="1000004", estado="cerrado", fecha=date(2026, 6, 1))
    activo = _ingreso(db_session, siniestro="1000004", estado="activo", fecha=date(2026, 1, 1))
    importar_reporte(db_session, FIXTURE.read_bytes())
    assert [o.identificador for o in _odas(db_session, activo.id)] == ["900004"]


def test_una_sola_vigente_por_ingreso_la_de_vencimiento_mas_tardio(db_session: Session):
    ing = _ingreso(db_session, siniestro="1000001")
    db_session.add(Oda(ingreso_id=ing.id, identificador="MANUAL-1",
                       fecha_vencimiento=date(2026, 5, 1), vigente=True))
    db_session.flush()
    importar_reporte(db_session, FIXTURE.read_bytes())
    odas = {o.identificador: o for o in _odas(db_session, ing.id)}
    assert [k for k, o in odas.items() if o.vigente] == ["900009"]  # vence 07-09-2026
    assert odas["900009"].fecha_registro == date(2026, 9, 1)
    assert odas["MANUAL-1"].vigente is False  # se conserva el historial


def test_importacion_idempotente_y_actualiza_si_cambia_la_vigencia(db_session: Session):
    ing = _ingreso(db_session, siniestro="S-IDEM")
    fin = HOY + timedelta(days=30)
    contenido = _xlsx([_fila(7001, "S-IDEM", fin)])

    r1 = importar_reporte(db_session, contenido)
    r2 = importar_reporte(db_session, contenido)
    assert (r1.creadas, r1.actualizadas, r1.sin_cambios) == (1, 0, 0)
    assert (r2.creadas, r2.actualizadas, r2.sin_cambios) == (0, 0, 1)
    assert len(_odas(db_session, ing.id)) == 1

    r3 = importar_reporte(db_session, _xlsx([_fila(7001, "S-IDEM", fin, cese=HOY + timedelta(days=2),
                                                    estado="CESADA")]))
    assert (r3.creadas, r3.actualizadas) == (0, 1)
    (oda,) = _odas(db_session, ing.id)
    assert oda.fecha_vencimiento == HOY + timedelta(days=2)


def test_por_vencer_solo_cuenta_pacientes_activos(db_session: Session):
    _ingreso(db_session, siniestro="S-ACT")
    _ingreso(db_session, siniestro="S-CER", estado="cerrado")
    pronto = HOY + timedelta(days=3)
    r = importar_reporte(
        db_session,
        _xlsx([_fila(8001, "S-ACT", pronto), _fila(8002, "S-CER", pronto),
               _fila(8003, "S-ACT", HOY + timedelta(days=90), tipo="Ambulatoria")]),
    )
    # La vigente de S-ACT es la de vencimiento más tardío (8003, lejana): no está por vencer.
    assert r.por_vencer_paciente_activo == []

    r = importar_reporte(db_session, _xlsx([_fila(8004, "S-ACT2", pronto)]))
    assert r.sin_paciente and not r.por_vencer_paciente_activo
    _ingreso(db_session, siniestro="S-ACT2")
    r = importar_reporte(db_session, _xlsx([_fila(8004, "S-ACT2", pronto), _fila(8002, "S-CER", pronto)]))
    assert [p.numero_orden for p in r.por_vencer_paciente_activo] == ["8004"]


# ── Alerta ODA_POR_VENCER: solo pacientes activos ─────────────────────────────


def test_alerta_oda_no_se_genera_para_paciente_cerrado(db_session: Session):
    activo = _ingreso(db_session, siniestro="S-AL-1")
    cerrado = _ingreso(db_session, siniestro="S-AL-2", estado="cerrado")
    pronto = HOY + timedelta(days=2)
    for ing, ident in ((activo, "AL-1"), (cerrado, "AL-2")):
        db_session.add(Oda(ingreso_id=ing.id, identificador=ident, fecha_vencimiento=pronto, vigente=True))
    db_session.flush()

    ids_hito = {h.caso_id for h in _construir_hitos_oda(db_session)}
    oda_activa, = _odas(db_session, activo.id)
    oda_cerrada, = _odas(db_session, cerrado.id)
    assert oda_activa.id in ids_hito and oda_cerrada.id not in ids_hito

    ejecutar_job_alertas(db_session, actor="test")
    casos = set(db_session.scalars(
        select(AlertaNotif.caso_id).where(AlertaNotif.tipo == TipoAlerta.ODA_POR_VENCER.value)
    ))
    assert oda_activa.id in casos and oda_cerrada.id not in casos


# ── Endpoint ───────────────────────────────────────────────────────────────────


def test_endpoint_dry_run_no_guarda(as_admin, db_session: Session):
    ing = _ingreso(db_session, siniestro="1000001")
    r = _subir(as_admin, FIXTURE.read_bytes(), dry_run=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is True
    assert body["filas_leidas"] == 10
    assert body["creadas"] == 2
    assert len(body["sin_paciente"]) == 8
    assert body["sin_paciente"][0]["numero_siniestro"]
    assert _odas(db_session, ing.id) == []
    assert not db_session.scalars(select(AuditLog).where(AuditLog.entity == "oda_importacion")).all()


def test_endpoint_importa_audita_y_es_idempotente(as_coordinacion, db_session: Session):
    ing = _ingreso(db_session, siniestro="S-EP")
    pronto = HOY + timedelta(days=3)
    contenido = _xlsx([_fila(9001, "S-EP", pronto), _fila(9002, "S-NADA", pronto)])

    r = _subir(as_coordinacion, contenido)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["creadas"], body["actualizadas"], body["por_vencer_paciente_activo"]) == (1, 0, 1)
    assert body["por_vencer"][0]["folio"] == ing.folio
    assert [s["numero_orden"] for s in body["sin_paciente"]] == ["9002"]
    (oda,) = _odas(db_session, ing.id)
    assert oda.vigente is True

    trazas = db_session.scalars(select(AuditLog).where(AuditLog.entity.in_(["oda", "oda_importacion"]))).all()
    assert {(t.entity, t.action) for t in trazas} == {("oda", "CREATE"), ("oda_importacion", "CREATE")}

    r2 = _subir(as_coordinacion, contenido).json()
    assert (r2["creadas"], r2["sin_cambios"]) == (0, 1)
    assert len(_odas(db_session, ing.id)) == 1


def test_endpoint_reporta_filas_con_error(as_admin):
    fin = HOY + timedelta(days=10)
    mala = _fila(2, "S2", fin)
    mala[2] = "no-es-fecha"
    body = _subir(as_admin, _xlsx([mala]), dry_run=True).json()
    assert body["errores"] == [{"fila": 2, "motivo": "Orden 2: fecha inválida «no-es-fecha»."}]


def test_endpoint_valida_archivo(as_admin):
    assert _subir(as_admin, b"x", nombre="reporte.csv").status_code == 415
    assert _subir(as_admin, b"no es excel").status_code == 422
    sin_siniestro = _xlsx([], encabezado=ENCABEZADO[:7])
    r = _subir(as_admin, sin_siniestro)
    assert r.status_code == 422 and "N° Siniestro" in r.json()["detail"]


def test_endpoint_rechaza_archivo_mayor_a_10mb(as_admin, monkeypatch):
    import app.routers.odas as odas_router

    monkeypatch.setattr(odas_router, "MAX_XLSX_BYTES", 100)
    assert _subir(as_admin, b"0" * 101).status_code == 413


def test_auditor_no_puede_importar(as_auditor):
    assert _subir(as_auditor, FIXTURE.read_bytes(), dry_run=True).status_code == 403
