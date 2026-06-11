"""Tests de los fixes de revisión del EPIC-05 (Auditoría).

Cada test valida exactamente el comportamiento corregido descrito en la revisión:
- C1: trazas READ se persisten (commit)
- I1: filtros diagnostico y profesional se aplican
- I2: EstadoReintegro.PARCIAL / TOTAL controla reintegro_parcial / total
- I3: fecha_diep_diat → fecha_denuncia; fecha_ingreso → fecha_derivacion
- M1: CSV no es vulnerable a inyección de fórmulas
- M2: altas se pueblan desde CasoReintegro en el reporte
- M3: fecha_calificacion_reca se obtiene de Reca.fecha_reca
- S2: n_sesiones_* y numero_sesiones_evaluacion retornan None
"""
from __future__ import annotations

import csv
import datetime
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro, Reca
from app.models.seguimiento import Seguimiento
from app.routers.auditoria import _sanitize_csv_cell
from app.schemas.auditoria import FiltrosReporte
from app.services.auditoria import generar_reporte, get_caso_consolidado


# ── Fixtures compartidos ───────────────────────────────────────────────────

@pytest.fixture
def paciente(db_session: Session) -> Paciente:
    p = Paciente(
        rut="200000001",
        nombre="Test Paciente",
        sexo="M",
        edad=40,
        region="Valparaíso",
    )
    db_session.add(p)
    db_session.flush()
    return p


@pytest.fixture
def ingreso_con_reca(db_session: Session, paciente: Paciente) -> tuple[Ingreso, CasoReintegro, Reca]:
    """Ingreso completo con CasoReintegro (estado TOTAL) y Reca."""
    ing = Ingreso(
        paciente_id=paciente.id,
        folio="FIX-2026-001",
        folio_manual=True,
        numero_siniestro="SIN-FIX-001",
        fecha_ingreso=datetime.date(2026, 3, 1),
        fecha_diep_diat=datetime.date(2026, 2, 15),   # I3: esta es la fecha_denuncia
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32.0 Episodio depresivo",
        estado="cerrado",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        eval_medica_fecha=datetime.date(2026, 3, 10),
        eval_medica_medico="Dr. Pérez Salud",
        eval_psico_fecha=datetime.date(2026, 3, 15),
        eval_psico_psicologo="Ps. García Mente",
        reca_ep_ec="F33.1 Trastorno depresivo recurrente",
        programa="ISL",
    )
    db_session.add(seg)
    db_session.flush()

    rei = CasoReintegro(
        ingreso_id=ing.id,
        rut=paciente.rut,
        nombre=paciente.nombre,
        tipo_derivacion="DIAT",
        fecha_caso=datetime.date(2026, 5, 1),
        sexo="M",
        edad=40,
        region="Valparaíso",
        estado_reintegro="total",
        fecha_reintegro=datetime.date(2026, 5, 20),
        alta_medica=True,
        fecha_alta_medica=datetime.date(2026, 5, 18),
        alta_psicologica=True,
        fecha_alta_psico=datetime.date(2026, 5, 19),
        tipo_alta="terapeutica",
    )
    db_session.add(rei)
    db_session.flush()

    reca = Reca(
        caso_reintegro_id=rei.id,
        fecha_reca=datetime.date(2026, 4, 10),
        tipo_reca="AT",
        numero_reca="RECA-2026-001",
        razon_social="Empresa SA",
    )
    db_session.add(reca)
    db_session.flush()

    return ing, rei, reca


@pytest.fixture
def ingreso_parcial(db_session: Session, paciente: Paciente) -> Ingreso:
    """Ingreso con CasoReintegro estado PARCIAL."""
    ing = Ingreso(
        paciente_id=paciente.id,
        folio="FIX-2026-002",
        folio_manual=True,
        numero_siniestro="SIN-FIX-002",
        fecha_ingreso=datetime.date(2026, 4, 1),
        tipo_derivacion="DIEP",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="G54.0 Ciática",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        eval_medica_medico="Dr. Rodríguez Columna",
        eval_psico_psicologo="Ps. Torres Alivio",
        reca_ep_ec="G54.0 Ciática crónica",
    )
    db_session.add(seg)

    rei = CasoReintegro(
        ingreso_id=ing.id,
        rut=paciente.rut,
        nombre=paciente.nombre,
        tipo_derivacion="DIEP",
        fecha_caso=datetime.date(2026, 4, 1),
        sexo="M",
        edad=40,
        region="Valparaíso",
        estado_reintegro="parcial",
        fecha_reintegro=datetime.date(2026, 5, 1),
        alta_medica=False,
        alta_psicologica=False,
    )
    db_session.add(rei)
    db_session.flush()
    return ing


# ── C1: trazas READ se persisten ───────────────────────────────────────────

def test_c1_traza_read_caso_persistida_tras_get(
    as_auditor: TestClient, db_session: Session, ingreso_con_reca: tuple
):
    """C1: después de GET /casos/{id}, el audit_log contiene una fila READ para auditoria_caso."""
    ing, _, _ = ingreso_con_reca
    r = as_auditor.get(f"/api/v1/auditoria/casos/{ing.id}")
    assert r.status_code == 200

    # La traza debe estar en la BD (db.commit() fue llamado en el router)
    trazas = list(db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity == "auditoria_caso")
        .where(AuditLog.entity_id == str(ing.id))
        .where(AuditLog.action == "READ")
    ))
    assert len(trazas) >= 1, "Traza READ no persistida — falta db.commit() en el router (C1)"


def test_c1_traza_read_busqueda_persistida(
    as_auditor: TestClient, db_session: Session, ingreso_con_reca: tuple
):
    """C1: GET /casos?rut=... persiste traza READ con entity=auditoria_busqueda."""
    r = as_auditor.get("/api/v1/auditoria/casos", params={"rut": "200000001"})
    assert r.status_code == 200

    trazas = list(db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity == "auditoria_busqueda")
        .where(AuditLog.action == "READ")
    ))
    assert len(trazas) >= 1, "Traza READ búsqueda no persistida (C1)"


def test_c1_traza_read_reporte_persistida(
    as_auditor: TestClient, db_session: Session
):
    """C1: POST /reportes persiste traza READ con entity=auditoria_reporte."""
    payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
    r = as_auditor.post("/api/v1/auditoria/reportes", json=payload)
    assert r.status_code == 200

    trazas = list(db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity == "auditoria_reporte")
        .where(AuditLog.action == "READ")
    ))
    assert len(trazas) >= 1, "Traza READ reporte no persistida (C1)"


def test_c1_traza_read_descarga_csv_persistida(
    as_auditor: TestClient, db_session: Session
):
    """C1: POST /reportes/descargar persiste traza READ con entity=auditoria_descarga_csv."""
    payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
    r = as_auditor.post("/api/v1/auditoria/reportes/descargar", json=payload)
    assert r.status_code == 200

    trazas = list(db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity == "auditoria_descarga_csv")
        .where(AuditLog.action == "READ")
    ))
    assert len(trazas) >= 1, "Traza READ descarga CSV no persistida (C1)"


# ── I1: filtros diagnostico y profesional ─────────────────────────────────

def test_i1_filtro_diagnostico_sobre_ingreso(
    db_session: Session, ingreso_con_reca: tuple
):
    """I1: filtro diagnostico hace OR sobre Ingreso.diagnostico (substring, case-insensitive)."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        diagnostico="episodio depresivo",  # substring lowercase de "F32.0 Episodio depresivo"
    )
    reporte = generar_reporte(db_session, filtros)
    folios = [f.folio for f in reporte.filas]
    assert "FIX-2026-001" in folios


def test_i1_filtro_diagnostico_sobre_reca_ep_ec(
    db_session: Session, ingreso_con_reca: tuple
):
    """I1: filtro diagnostico hace OR sobre Seguimiento.reca_ep_ec (post-RECA)."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        diagnostico="trastorno depresivo recurrente",  # en reca_ep_ec
    )
    reporte = generar_reporte(db_session, filtros)
    folios = [f.folio for f in reporte.filas]
    assert "FIX-2026-001" in folios


def test_i1_filtro_diagnostico_no_match_excluye(
    db_session: Session, ingreso_con_reca: tuple
):
    """I1: un diagnóstico que no coincide con ninguno de los dos campos excluye la fila."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        diagnostico="DIAGNÓSTICO_INEXISTENTE_XYZ",
    )
    reporte = generar_reporte(db_session, filtros)
    assert reporte.total == 0


def test_i1_filtro_profesional_sobre_medico(
    db_session: Session, ingreso_con_reca: tuple
):
    """I1: filtro profesional hace OR sobre eval_medica_medico (substring case-insensitive)."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        profesional="Pérez",  # en eval_medica_medico = "Dr. Pérez Salud"
    )
    reporte = generar_reporte(db_session, filtros)
    folios = [f.folio for f in reporte.filas]
    assert "FIX-2026-001" in folios


def test_i1_filtro_profesional_sobre_psicologo(
    db_session: Session, ingreso_con_reca: tuple
):
    """I1: filtro profesional hace OR sobre eval_psico_psicologo."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        profesional="García",  # en eval_psico_psicologo = "Ps. García Mente"
    )
    reporte = generar_reporte(db_session, filtros)
    folios = [f.folio for f in reporte.filas]
    assert "FIX-2026-001" in folios


def test_i1_filtro_profesional_no_match_excluye(
    db_session: Session, ingreso_con_reca: tuple
):
    """I1: un profesional que no coincide excluye la fila."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        profesional="PROFESIONAL_INEXISTENTE_XYZ",
    )
    reporte = generar_reporte(db_session, filtros)
    assert reporte.total == 0


# ── I2: EstadoReintegro para reintegro_parcial / total ────────────────────

def test_i2_estado_total_en_caso_consolidado(
    db_session: Session, ingreso_con_reca: tuple
):
    """I2: estado_reintegro=TOTAL → reintegro_total=True, reintegro_parcial=False."""
    ing, _, _ = ingreso_con_reca
    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.controles.reintegro_total is True
    assert caso.controles.reintegro_parcial is False


def test_i2_estado_parcial_en_caso_consolidado(
    db_session: Session, ingreso_parcial: Ingreso
):
    """I2: estado_reintegro=PARCIAL → reintegro_parcial=True, reintegro_total=False."""
    caso = get_caso_consolidado(db_session, ingreso_parcial.id)
    assert caso is not None
    assert caso.controles.reintegro_parcial is True
    assert caso.controles.reintegro_total is False


def test_i2_estado_total_en_reporte(
    db_session: Session, ingreso_con_reca: tuple
):
    """I2: reporte con estado_reintegro=TOTAL reporta reintegro_total=True."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)
    fila = next((f for f in reporte.filas if f.folio == "FIX-2026-001"), None)
    assert fila is not None
    assert fila.reintegro_total is True
    assert fila.reintegro_parcial is False


def test_i2_fecha_reintegro_total_correcta(
    db_session: Session, ingreso_con_reca: tuple
):
    """I2: fecha_reintegro_total se asigna cuando estado es TOTAL."""
    ing, _, _ = ingreso_con_reca
    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.controles.fecha_reintegro_total == datetime.date(2026, 5, 20)
    assert caso.controles.fecha_reintegro_parcial is None  # no está en PARCIAL


def test_i2_fecha_reintegro_parcial_correcta(
    db_session: Session, ingreso_parcial: Ingreso
):
    """I2: fecha_reintegro_parcial se asigna cuando estado es PARCIAL."""
    caso = get_caso_consolidado(db_session, ingreso_parcial.id)
    assert caso is not None
    assert caso.controles.fecha_reintegro_parcial == datetime.date(2026, 5, 1)
    assert caso.controles.fecha_reintegro_total is None


# ── I3: fecha_denuncia → fecha_diep_diat, fecha_derivacion → fecha_ingreso ─

def test_i3_fecha_denuncia_es_fecha_diep_diat(
    db_session: Session, ingreso_con_reca: tuple
):
    """I3: datos_caso.fecha_denuncia mapea a Ingreso.fecha_diep_diat."""
    ing, _, _ = ingreso_con_reca
    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.datos_caso.fecha_denuncia == datetime.date(2026, 2, 15)  # fecha_diep_diat


def test_i3_fecha_derivacion_es_fecha_ingreso(
    db_session: Session, ingreso_con_reca: tuple
):
    """I3: datos_caso.fecha_derivacion mapea a Ingreso.fecha_ingreso."""
    ing, _, _ = ingreso_con_reca
    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.datos_caso.fecha_derivacion == datetime.date(2026, 3, 1)  # fecha_ingreso


def test_i3_fecha_denuncia_reporte_es_fecha_diep_diat(
    db_session: Session, ingreso_con_reca: tuple
):
    """I3: fila del reporte mapea fecha_denuncia a Ingreso.fecha_diep_diat."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)
    fila = next((f for f in reporte.filas if f.folio == "FIX-2026-001"), None)
    assert fila is not None
    assert fila.fecha_denuncia == datetime.date(2026, 2, 15)  # fecha_diep_diat


def test_i3_fecha_denuncia_none_cuando_no_hay_diep_diat(
    db_session: Session, paciente: Paciente
):
    """I3: fecha_denuncia es None si no se registró fecha_diep_diat (campo opcional)."""
    ing = Ingreso(
        paciente_id=paciente.id,
        folio="FIX-2026-003",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 6, 1),
        fecha_diep_diat=None,  # no se registró
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F41.0",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.datos_caso.fecha_denuncia is None
    assert caso.datos_caso.fecha_derivacion == datetime.date(2026, 6, 1)


# ── M1: CSV formula injection guard ───────────────────────────────────────

def test_m1_sanitize_prefija_igual():
    """M1: valor que empieza con = recibe prefijo '."""
    assert _sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"


def test_m1_sanitize_prefija_mas():
    """M1: valor que empieza con + recibe prefijo '."""
    assert _sanitize_csv_cell("+1") == "'+1"


def test_m1_sanitize_prefija_menos():
    """M1: valor que empieza con - recibe prefijo '."""
    assert _sanitize_csv_cell("-1") == "'-1"


def test_m1_sanitize_prefija_arroba():
    """M1: valor que empieza con @ recibe prefijo '."""
    assert _sanitize_csv_cell("@SUM") == "'@SUM"


def test_m1_sanitize_no_modifica_valores_normales():
    """M1: valores normales no se modifican."""
    assert _sanitize_csv_cell("Ana González") == "Ana González"
    assert _sanitize_csv_cell("F32.0 Depresión") == "F32.0 Depresión"
    assert _sanitize_csv_cell("") == ""


def test_m1_csv_sin_inyeccion_en_nombre_malicioso(
    as_auditor: TestClient, db_session: Session, paciente: Paciente
):
    """M1: CSV descargado sanitiza nombres/diagnósticos con prefijos de fórmula."""
    ing = Ingreso(
        paciente_id=paciente.id,
        folio="=INJECT-001",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 7, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="=CMD|' /C calc'!A0",
        estado="activo",
    )
    # Actualizamos también el nombre del paciente en el fixture
    paciente.nombre = "=HYPERLINK()"
    db_session.add(ing)
    db_session.flush()

    payload = {"fecha_desde": "2026-07-01", "fecha_hasta": "2026-07-31"}
    r = as_auditor.post("/api/v1/auditoria/reportes/descargar", json=payload)
    assert r.status_code == 200

    reader = csv.reader(io.StringIO(r.text))
    rows = list(reader)
    # Hay al menos el encabezado + 1 fila
    assert len(rows) >= 2
    # En ninguna celda de string de los datos debe aparecer un valor iniciando con = sin '
    for row in rows[1:]:
        for cell in row:
            if cell.startswith("=") or cell.startswith("+CMD"):
                pytest.fail(f"Celda con posible inyección CSV sin sanitizar: {cell!r}")


# ── M2: altas pobladas en el reporte ──────────────────────────────────────

def test_m2_altas_pobladas_en_fila_reporte(
    db_session: Session, ingreso_con_reca: tuple
):
    """M2: alta_medica, alta_psicologica, alta_terapeutica se pueblan desde CasoReintegro."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)
    fila = next((f for f in reporte.filas if f.folio == "FIX-2026-001"), None)
    assert fila is not None
    assert fila.alta_medica is True       # CasoReintegro.alta_medica = True
    assert fila.alta_psicologica is True  # CasoReintegro.alta_psicologica = True
    assert fila.alta_terapeutica is True  # CasoReintegro.tipo_alta = "terapeutica"


def test_m2_altas_falsas_cuando_no_hay_reintegro(
    db_session: Session, paciente: Paciente
):
    """M2: sin CasoReintegro, altas son False."""
    ing = Ingreso(
        paciente_id=paciente.id,
        folio="FIX-2026-004",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 8, 1),
        tipo_derivacion="DIEP",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F40.1 Fobia",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 8, 1),
        fecha_hasta=datetime.date(2026, 8, 31),
    )
    reporte = generar_reporte(db_session, filtros)
    fila = next((f for f in reporte.filas if f.folio == "FIX-2026-004"), None)
    assert fila is not None
    assert fila.alta_medica is False
    assert fila.alta_psicologica is False
    assert fila.alta_terapeutica is False


# ── M3: fecha_calificacion_reca desde Reca.fecha_reca ────────────────────

def test_m3_fecha_calificacion_reca_en_caso_consolidado(
    db_session: Session, ingreso_con_reca: tuple
):
    """M3: evaluaciones.fecha_calificacion_reca viene de Reca.fecha_reca."""
    ing, _, reca = ingreso_con_reca
    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.evaluaciones.fecha_calificacion_reca == datetime.date(2026, 4, 10)


def test_m3_fecha_calificacion_reca_en_reporte(
    db_session: Session, ingreso_con_reca: tuple
):
    """M3: fila del reporte tiene fecha_calificacion_reca de Reca.fecha_reca."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)
    fila = next((f for f in reporte.filas if f.folio == "FIX-2026-001"), None)
    assert fila is not None
    assert fila.fecha_calificacion_reca == datetime.date(2026, 4, 10)


def test_m3_fecha_calificacion_reca_none_sin_reca(
    db_session: Session, paciente: Paciente
):
    """M3: sin Reca asociada, fecha_calificacion_reca es None."""
    ing = Ingreso(
        paciente_id=paciente.id,
        folio="FIX-2026-005",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 9, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F43.1",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.evaluaciones.fecha_calificacion_reca is None


# ── S2: n_sesiones_* y numero_sesiones_evaluacion retornan None ────────────

def test_s2_sesiones_son_none_en_caso_consolidado(
    db_session: Session, ingreso_con_reca: tuple
):
    """S2: todos los campos n_sesiones_* retornan None (dato no existe en el modelo)."""
    ing, _, _ = ingreso_con_reca
    caso = get_caso_consolidado(db_session, ing.id)
    assert caso is not None
    assert caso.evaluaciones.numero_sesiones_evaluacion is None
    assert caso.controles.n_sesiones_medicas is None
    assert caso.controles.n_sesiones_psicologicas is None
    assert caso.controles.n_sesiones_ampliacion is None


def test_s2_sesiones_son_none_en_api(
    as_auditor: TestClient, db_session: Session, ingreso_con_reca: tuple
):
    """S2: la respuesta JSON de /casos/{id} devuelve null para n_sesiones_*."""
    ing, _, _ = ingreso_con_reca
    r = as_auditor.get(f"/api/v1/auditoria/casos/{ing.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["evaluaciones"]["numero_sesiones_evaluacion"] is None
    assert body["controles"]["n_sesiones_medicas"] is None
    assert body["controles"]["n_sesiones_psicologicas"] is None
    assert body["controles"]["n_sesiones_ampliacion"] is None
