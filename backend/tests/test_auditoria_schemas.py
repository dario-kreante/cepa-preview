"""Tests unitarios de los schemas de auditoría (sin BD)."""
import datetime

import pytest
from pydantic import ValidationError

from app.schemas.auditoria import (
    CasoConsolidadoRead,
    FilaReporteRead,
    FiltrosReporte,
    ReporteAuditoriaRead,
    SeccionCierreRead,
    SeccionControlesRead,
    SeccionDatosCasoRead,
    SeccionEvaluacionesRead,
)


# ── SeccionDatosCasoRead ───────────────────────────────────────────────────

def test_seccion_datos_caso_campos_minimos():
    datos = SeccionDatosCasoRead(
        folio="2026-0123",
        numero_siniestro="SIN-2026-001",
        fecha_denuncia=datetime.date(2026, 1, 15),
        tipo_denuncia="DIAT",
        fecha_derivacion=datetime.date(2026, 1, 20),
        nombre_completo="Ana González",
        rut="123456785",
        region="Maule",
    )
    assert datos.folio == "2026-0123"
    assert datos.region == "Maule"


def test_seccion_datos_caso_campos_opcionales_son_none_por_defecto():
    datos = SeccionDatosCasoRead(
        folio="2026-0124",
        numero_siniestro=None,
        fecha_denuncia=None,
        tipo_denuncia=None,
        fecha_derivacion=None,
        nombre_completo="Pedro Díaz",
        rut="87654321K",
        region=None,
    )
    assert datos.numero_siniestro is None
    assert datos.fecha_derivacion is None


# ── SeccionEvaluacionesRead ────────────────────────────────────────────────

def test_seccion_evaluaciones_diagnoticos_separados():
    ev = SeccionEvaluacionesRead(
        fecha_eval_medica=datetime.date(2026, 2, 1),
        fecha_eval_psicologica=datetime.date(2026, 2, 5),
        fecha_calificacion_reca=datetime.date(2026, 3, 1),
        diagnostico_inicial="F32.0 Episodio depresivo leve",
        diagnostico_post_reca="F33.1 Trastorno depresivo recurrente",
        numero_sesiones_evaluacion=3,
    )
    assert ev.diagnostico_inicial != ev.diagnostico_post_reca
    assert ev.fecha_calificacion_reca == datetime.date(2026, 3, 1)


def test_seccion_evaluaciones_todos_opcionales():
    ev = SeccionEvaluacionesRead(
        fecha_eval_medica=None,
        fecha_eval_psicologica=None,
        fecha_calificacion_reca=None,
        diagnostico_inicial=None,
        diagnostico_post_reca=None,
        numero_sesiones_evaluacion=0,
    )
    assert ev.numero_sesiones_evaluacion == 0


# ── SeccionControlesRead ───────────────────────────────────────────────────

def test_seccion_controles_campos_completos():
    ctrl = SeccionControlesRead(
        fecha_primera_consulta_medica=datetime.date(2026, 3, 10),
        fecha_primera_consulta_psicologica=datetime.date(2026, 3, 12),
        n_sesiones_medicas=5,
        n_sesiones_psicologicas=8,
        n_sesiones_ampliacion=2,
        reintegro_parcial=True,
        fecha_reintegro_parcial=datetime.date(2026, 5, 1),
        reintegro_total=False,
        fecha_reintegro_total=None,
    )
    assert ctrl.reintegro_parcial is True
    assert ctrl.fecha_reintegro_total is None


# ── SeccionCierreRead ──────────────────────────────────────────────────────

def test_seccion_cierre_pendiente_cuando_sin_altas():
    """CA-5 / TC-050-04: caso en tratamiento sin altas registradas."""
    cierre = SeccionCierreRead(
        alta_medica=False,
        fecha_alta_medica=None,
        alta_psicologica=False,
        fecha_alta_psicologica=None,
        alta_terapeutica=False,
        fecha_alta_terapeutica=None,
        estado_general=None,
        observaciones=None,
    )
    assert cierre.alta_medica is False
    assert cierre.estado_general is None


def test_seccion_cierre_con_altas_parciales():
    cierre = SeccionCierreRead(
        alta_medica=True,
        fecha_alta_medica=datetime.date(2026, 6, 1),
        alta_psicologica=False,
        fecha_alta_psicologica=None,
        alta_terapeutica=False,
        fecha_alta_terapeutica=None,
        estado_general="cerrado",
        observaciones="Alta médica emitida; psicología en curso.",
    )
    assert cierre.alta_medica is True
    assert cierre.alta_psicologica is False


# ── CasoConsolidadoRead ────────────────────────────────────────────────────

def test_caso_consolidado_contiene_todas_las_secciones():
    caso = CasoConsolidadoRead(
        ingreso_id=1,
        datos_caso=SeccionDatosCasoRead(
            folio="2026-0123",
            numero_siniestro="SIN-001",
            fecha_denuncia=datetime.date(2026, 1, 15),
            tipo_denuncia="DIAT",
            fecha_derivacion=datetime.date(2026, 1, 20),
            nombre_completo="Ana González",
            rut="123456785",
            region="Maule",
        ),
        evaluaciones=SeccionEvaluacionesRead(
            fecha_eval_medica=None,
            fecha_eval_psicologica=None,
            fecha_calificacion_reca=None,
            diagnostico_inicial="F32.0",
            diagnostico_post_reca=None,
            numero_sesiones_evaluacion=0,
        ),
        controles=SeccionControlesRead(
            fecha_primera_consulta_medica=None,
            fecha_primera_consulta_psicologica=None,
            n_sesiones_medicas=0,
            n_sesiones_psicologicas=0,
            n_sesiones_ampliacion=0,
            reintegro_parcial=False,
            fecha_reintegro_parcial=None,
            reintegro_total=False,
            fecha_reintegro_total=None,
        ),
        cierre=SeccionCierreRead(
            alta_medica=False,
            fecha_alta_medica=None,
            alta_psicologica=False,
            fecha_alta_psicologica=None,
            alta_terapeutica=False,
            fecha_alta_terapeutica=None,
            estado_general=None,
            observaciones=None,
        ),
    )
    assert caso.ingreso_id == 1
    assert caso.datos_caso.folio == "2026-0123"
    assert caso.cierre.alta_medica is False


# ── FiltrosReporte ─────────────────────────────────────────────────────────

def test_filtros_periodo_obligatorio():
    """RN-2: el período es obligatorio para acotar el universo del reporte."""
    with pytest.raises(ValidationError):
        FiltrosReporte(fecha_desde=None, fecha_hasta=None)


def test_filtros_periodo_minimo_valido():
    f = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    assert f.fecha_desde == datetime.date(2026, 1, 1)
    assert f.diagnostico is None
    assert f.profesional is None
    assert f.estado_caso is None
    assert f.programa is None
    assert f.tipo_alta is None
    assert f.region is None
    assert f.tipo_ingreso is None


def test_filtros_todos_los_campos():
    f = FiltrosReporte(
        fecha_desde=datetime.date(2026, 5, 1),
        fecha_hasta=datetime.date(2026, 5, 31),
        diagnostico="F32.0",
        profesional="Dr. Juan Pérez",
        estado_caso="activo",
        programa="Programa ISL",
        tipo_alta="terapeutica",
        region="Maule",
        tipo_ingreso="convenio",
    )
    assert f.estado_caso == "activo"
    assert f.tipo_alta == "terapeutica"


# ── FilaReporteRead ────────────────────────────────────────────────────────

def test_fila_reporte_trazable_por_folio_y_siniestro():
    """CA-3 / TC-051-03: cada fila es trazable a folio + número de siniestro."""
    fila = FilaReporteRead(
        ingreso_id=42,
        folio="2026-0123",
        numero_siniestro="SIN-001",
        rut="123456785",
        nombre_completo="Ana González",
        region="Maule",
        fecha_denuncia=datetime.date(2026, 1, 15),
        tipo_denuncia="DIAT",
        estado_caso="activo",
        diagnostico_inicial="F32.0",
        diagnostico_post_reca=None,
        profesional=None,
        fecha_calificacion_reca=None,
        reintegro_parcial=False,
        reintegro_total=False,
        alta_medica=False,
        alta_psicologica=False,
        alta_terapeutica=False,
    )
    assert fila.folio == "2026-0123"
    assert fila.numero_siniestro == "SIN-001"
    assert fila.ingreso_id == 42


# ── ReporteAuditoriaRead ───────────────────────────────────────────────────

def test_reporte_con_lista_vacia_es_valido():
    """CA-4 / TC-051-04: resultado vacío es válido."""
    reporte = ReporteAuditoriaRead(
        filtros_aplicados=FiltrosReporte(
            fecha_desde=datetime.date(2026, 1, 1),
            fecha_hasta=datetime.date(2026, 1, 31),
        ),
        total=0,
        filas=[],
    )
    assert reporte.total == 0
    assert reporte.filas == []
