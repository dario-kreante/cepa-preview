"""Tests del servicio de agregación de auditoría.

Los datos se crean directamente vía los modelos reales del sistema (EPIC-01..07).
Cada test trabaja sobre la BD de pruebas con rollback automático (fixture db_session).

DESVIACIONES respecto al plan original (declaradas):
- Seguimiento: usa eval_medica_fecha / eval_psico_fecha (no fecha_eval_medica/psicologica).
  No tiene campos n_sesiones_*, alta_medica, diagnostico_post_reca.
- Reintegro: el modelo real es CasoReintegro (no Reintegro); campos alta_medica,
  alta_psicologica, fecha_alta_psico (no fecha_alta_psicologica).
  alta_terapeutica se deduce de tipo_alta == "terapeutica".
- Ingreso: fecha_ingreso (no fecha_denuncia), tipo_derivacion (no tipo_denuncia),
  estado (no estado_caso), diagnostico (no diagnostico_inicial), sin fecha_derivacion ni programa.
"""
from __future__ import annotations

import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro
from app.models.seguimiento import Seguimiento
from app.schemas.auditoria import FiltrosReporte
from app.services.auditoria import generar_reporte, get_caso_consolidado


# ── Fixtures de datos de prueba ────────────────────────────────────────────

@pytest.fixture
def paciente_base(db_session: Session) -> Paciente:
    p = Paciente(
        rut="123456785",
        nombre="Ana González",
        sexo="F",
        edad=35,
        region="Maule",
    )
    db_session.add(p)
    db_session.flush()
    return p


@pytest.fixture
def ingreso_completo(db_session: Session, paciente_base: Paciente) -> Ingreso:
    """Ingreso con datos en todas las secciones §7.5.1..§7.5.4."""
    ing = Ingreso(
        paciente_id=paciente_base.id,
        folio="2026-0123",
        folio_manual=True,
        numero_siniestro="SIN-2026-001",
        fecha_ingreso=datetime.date(2026, 1, 15),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32.0 Episodio depresivo leve",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        eval_medica_fecha=datetime.date(2026, 2, 1),
        eval_medica_medico="Dr. Juan Pérez",
        eval_psico_fecha=datetime.date(2026, 2, 5),
        eval_psico_psicologo="Ps. María López",
        reca_ep_ec="F33.1 Trastorno depresivo recurrente",
        programa="Programa ISL",
    )
    db_session.add(seg)

    rei = CasoReintegro(
        ingreso_id=ing.id,
        rut=paciente_base.rut,
        nombre=paciente_base.nombre,
        tipo_derivacion="DIAT",
        fecha_caso=datetime.date(2026, 5, 1),
        sexo="F",
        edad=35,
        region="Maule",
        alta_medica=False,
        alta_psicologica=False,
        tipo_alta=None,
    )
    db_session.add(rei)
    db_session.flush()
    return ing


@pytest.fixture
def ingreso_sin_altas(db_session: Session, paciente_base: Paciente) -> Ingreso:
    """TC-050-04: caso en tratamiento sin altas."""
    ing = Ingreso(
        paciente_id=paciente_base.id,
        folio="2026-0124",
        folio_manual=True,
        numero_siniestro="SIN-2026-002",
        fecha_ingreso=datetime.date(2026, 2, 1),
        tipo_derivacion="DIEP",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F41.1",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        eval_medica_fecha=None,
        eval_psico_fecha=None,
        reca_ep_ec=None,
        programa=None,
    )
    db_session.add(seg)
    db_session.flush()
    return ing


# ── TC-050-01: vista consolidada con datos en todos los módulos ────────────

def test_get_caso_consolidado_devuelve_todas_las_secciones(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-1 / TC-050-01: GET por ingreso_id devuelve §7.5.1–§7.5.4 consolidados."""
    caso = get_caso_consolidado(db_session, ingreso_completo.id)

    assert caso is not None
    assert caso.ingreso_id == ingreso_completo.id

    # §7.5.1 datos del caso
    assert caso.datos_caso.folio == "2026-0123"
    assert caso.datos_caso.numero_siniestro == "SIN-2026-001"
    assert caso.datos_caso.rut == "123456785"
    assert caso.datos_caso.region == "Maule"

    # §7.5.2 evaluaciones — diagnostico_inicial del Ingreso, post_reca del Seguimiento.reca_ep_ec
    assert caso.evaluaciones.diagnostico_inicial == "F32.0 Episodio depresivo leve"
    assert caso.evaluaciones.diagnostico_post_reca == "F33.1 Trastorno depresivo recurrente"
    assert caso.evaluaciones.fecha_eval_medica == datetime.date(2026, 2, 1)

    # §7.5.3 controles — reintegro derivado de CasoReintegro
    assert caso.controles.reintegro_parcial is False

    # §7.5.4 cierre — altas derivadas de CasoReintegro
    assert caso.cierre.alta_medica is False


# ── TC-050-02: siniestros diferenciados bajo el mismo RUT ─────────────────

def test_siniestros_distintos_no_se_mezclan(db_session: Session, paciente_base: Paciente):
    """CA-2 / TC-050-02: dos denuncias bajo el mismo RUT se presentan diferenciadas."""
    ing1 = Ingreso(
        paciente_id=paciente_base.id,
        folio="2020-0001",
        folio_manual=True,
        numero_siniestro="SIN-2020-DIAT",
        fecha_ingreso=datetime.date(2020, 6, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32.0",
        estado="cerrado",
    )
    ing2 = Ingreso(
        paciente_id=paciente_base.id,
        folio="2026-0200",
        folio_manual=True,
        numero_siniestro="SIN-2026-DIEP",
        fecha_ingreso=datetime.date(2026, 3, 1),
        tipo_derivacion="DIEP",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F41.1",
        estado="activo",
    )
    for ing in [ing1, ing2]:
        db_session.add(ing)
    db_session.flush()

    for ing in [ing1, ing2]:
        seg = Seguimiento(
            ingreso_id=ing.id,
            eval_medica_fecha=None,
            eval_psico_fecha=None,
        )
        db_session.add(seg)
    db_session.flush()

    caso1 = get_caso_consolidado(db_session, ing1.id)
    caso2 = get_caso_consolidado(db_session, ing2.id)

    assert caso1.datos_caso.numero_siniestro == "SIN-2020-DIAT"
    assert caso2.datos_caso.numero_siniestro == "SIN-2026-DIEP"
    assert caso1.datos_caso.folio != caso2.datos_caso.folio


# ── TC-050-03: diagnósticos inicial y post-RECA por separado ──────────────

def test_diagnosticos_se_muestran_por_separado(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-3 / TC-050-03: diagnóstico inicial (Ingreso.diagnostico) y
    post-RECA (Seguimiento.reca_ep_ec) visibles por separado."""
    caso = get_caso_consolidado(db_session, ingreso_completo.id)
    ev = caso.evaluaciones
    assert ev.diagnostico_inicial is not None
    assert ev.diagnostico_post_reca is not None
    assert ev.diagnostico_inicial != ev.diagnostico_post_reca


# ── TC-050-04: caso sin altas — cierre pendiente sin bloquear el resto ────

def test_caso_sin_altas_cierre_pendiente(
    db_session: Session, ingreso_sin_altas: Ingreso
):
    """CA-5 / TC-050-04: cierre vacío/pendiente no bloquea visualización del resto."""
    caso = get_caso_consolidado(db_session, ingreso_sin_altas.id)

    assert caso.cierre.alta_medica is False
    assert caso.cierre.alta_psicologica is False
    assert caso.cierre.alta_terapeutica is False
    assert caso.cierre.estado_general is None
    # resto de hitos visible sin error
    assert caso.datos_caso.folio == "2026-0124"
    assert caso.evaluaciones.numero_sesiones_evaluacion is None  # S2: dato no existe


# ── TC-050-06: ingreso_id inexistente devuelve None ────────────────────────

def test_caso_inexistente_devuelve_none(db_session: Session):
    resultado = get_caso_consolidado(db_session, ingreso_id=999999)
    assert resultado is None


# ── TC-051-01: reporte con filtros combinados ──────────────────────────────

def test_reporte_filtros_combinados(
    db_session: Session, ingreso_completo: Ingreso, ingreso_sin_altas: Ingreso
):
    """CA-1 / TC-051-01: solo retorna casos que cumplen todos los filtros (AND)."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
        estado_caso="activo",
        tipo_ingreso="convenio",
        tipo_denuncia="DIAT",
    )
    reporte = generar_reporte(db_session, filtros)

    folios = [f.folio for f in reporte.filas]
    assert "2026-0123" in folios       # DIAT + activo → debe aparecer
    assert "2026-0124" not in folios   # DIEP → no cumple tipo_denuncia="DIAT"
    assert reporte.total == len(reporte.filas)


# ── TC-051-04: reporte vacío cuando no hay coincidencias ──────────────────

def test_reporte_vacio_sin_coincidencias(db_session: Session, ingreso_completo: Ingreso):
    """CA-4 / TC-051-04: resultado vacío con mensaje implícito en total=0."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2000, 1, 1),
        fecha_hasta=datetime.date(2000, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)

    assert reporte.total == 0
    assert reporte.filas == []


# ── TC-051-03: trazabilidad por folio + siniestro ─────────────────────────

def test_reporte_filas_trazables_por_folio_y_siniestro(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-3 / TC-051-03: cada fila contiene folio e ingreso_id para trazabilidad."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 1, 1),
        fecha_hasta=datetime.date(2026, 12, 31),
    )
    reporte = generar_reporte(db_session, filtros)

    fila = next(f for f in reporte.filas if f.folio == "2026-0123")
    assert fila.numero_siniestro == "SIN-2026-001"
    assert fila.ingreso_id == ingreso_completo.id


# ── Filtros_aplicados conservados en el reporte ───────────────────────────

def test_reporte_conserva_filtros_aplicados_como_metadatos(
    db_session: Session, ingreso_completo: Ingreso
):
    """CA-2 / TC-051-02: los filtros se devuelven como metadatos en la respuesta."""
    filtros = FiltrosReporte(
        fecha_desde=datetime.date(2026, 5, 1),
        fecha_hasta=datetime.date(2026, 5, 31),
        estado_caso="activo",
    )
    reporte = generar_reporte(db_session, filtros)

    assert reporte.filtros_aplicados.fecha_desde == datetime.date(2026, 5, 1)
    assert reporte.filtros_aplicados.estado_caso == "activo"
