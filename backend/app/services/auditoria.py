"""Servicio de agregación de auditoría (EPIC-05).

Solo lectura: agrega datos de los módulos fuente vía ORM portable (sin SQL específico
de motor). No modifica datos clínicos (RN-1, CA-4).

ADAPTACIONES respecto al plan original (declaradas):
- Seguimiento real: eval_medica_fecha / eval_psico_fecha (no fecha_eval_medica/psicologica).
  reca_ep_ec mapea a diagnostico_post_reca. Sin campos n_sesiones_* ni alta_*.
- Ingreso real: fecha_ingreso (→ fecha_denuncia DTO), tipo_derivacion (→ tipo_denuncia DTO),
  estado (→ estado_caso DTO). diagnostico mapea a diagnostico_inicial.
  programa vive en Seguimiento.programa.
- Reintegro real: modelo CasoReintegro (no Reintegro). Campos alta_medica, alta_psicologica,
  fecha_alta_psico (no fecha_alta_psicologica). alta_terapeutica se deduce de tipo_alta.
- CasoReintegro no tiene FK directa a ingreso en la relación ORM del modelo Ingreso,
  por lo que se consulta directamente con where(ingreso_id == ...).
- numero_sesiones_evaluacion, n_sesiones_medicas/psicologicas/ampliacion: no existen
  en el modelo real → se retornan como 0 (campos contadores futuros).
"""
from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro
from app.models.seguimiento import Seguimiento
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


def get_caso_consolidado(db: Session, ingreso_id: int) -> CasoConsolidadoRead | None:
    """Retorna la vista consolidada de un caso por ingreso_id.

    Agrega §7.5.1..§7.5.4 desde los módulos fuente. Si el ingreso no existe,
    retorna None (el router responderá 404).

    Siniestros múltiples bajo el mismo RUT se diferencian por ingreso_id (CA-2, RN-3).

    Mapeo de campos reales:
    - Ingreso.fecha_ingreso → datos_caso.fecha_denuncia
    - Ingreso.tipo_derivacion → datos_caso.tipo_denuncia
    - Ingreso.diagnostico → evaluaciones.diagnostico_inicial
    - Seguimiento.reca_ep_ec → evaluaciones.diagnostico_post_reca
    - Seguimiento.eval_medica_fecha → evaluaciones.fecha_eval_medica
    - Seguimiento.eval_psico_fecha → evaluaciones.fecha_eval_psicologica
    - CasoReintegro.alta_medica / alta_psicologica → cierre.alta_medica / alta_psicologica
    - CasoReintegro.tipo_alta == "terapeutica" → cierre.alta_terapeutica
    """
    ingreso: Ingreso | None = db.scalar(
        select(Ingreso).where(Ingreso.id == ingreso_id)
    )
    if ingreso is None:
        return None

    paciente: Paciente = db.get(Paciente, ingreso.paciente_id)  # type: ignore[assignment]

    # Seguimiento (§7.5.2 + médico tratante)
    seg: Seguimiento | None = db.scalar(
        select(Seguimiento).where(Seguimiento.ingreso_id == ingreso_id)
    )

    # CasoReintegro (§7.5.4 altas — mapea a SeccionCierreRead)
    rei: CasoReintegro | None = db.scalar(
        select(CasoReintegro).where(CasoReintegro.ingreso_id == ingreso_id)
    )

    # §7.5.1 Datos del caso
    datos_caso = SeccionDatosCasoRead(
        folio=ingreso.folio,
        numero_siniestro=ingreso.numero_siniestro,
        fecha_denuncia=ingreso.fecha_ingreso,        # Ingreso.fecha_ingreso → DTO fecha_denuncia
        tipo_denuncia=ingreso.tipo_derivacion,       # Ingreso.tipo_derivacion → DTO tipo_denuncia
        fecha_derivacion=None,                       # campo no existe en el modelo real
        nombre_completo=paciente.nombre,
        rut=paciente.rut,
        region=paciente.region,
    )

    # §7.5.2 Evaluaciones
    # diagnostico_inicial: Ingreso.diagnostico (diagnóstico de ingreso)
    # diagnostico_post_reca: Seguimiento.reca_ep_ec (diagnóstico post-RECA)
    # numero_sesiones_evaluacion: no existe en el modelo real → 0
    evaluaciones = SeccionEvaluacionesRead(
        fecha_eval_medica=seg.eval_medica_fecha if seg else None,
        fecha_eval_psicologica=seg.eval_psico_fecha if seg else None,
        fecha_calificacion_reca=None,              # campo no existe en Seguimiento real
        diagnostico_inicial=ingreso.diagnostico,
        diagnostico_post_reca=seg.reca_ep_ec if seg else None,
        numero_sesiones_evaluacion=0,              # contador futuro, no existe en el modelo real
    )

    # §7.5.3 Controles y tratamiento
    # n_sesiones_* no existen en los modelos reales → 0
    # reintegro_parcial / total inferidos de CasoReintegro
    reintegro_parcial = bool(rei and rei.fecha_reintegro is not None)
    reintegro_total = bool(
        rei and rei.tipo_alta in ("medica", "psicologica", "terapeutica")
        and rei.alta_medica and rei.alta_psicologica
    )
    controles = SeccionControlesRead(
        fecha_primera_consulta_medica=None,        # campo no existe en el modelo real
        fecha_primera_consulta_psicologica=None,   # campo no existe en el modelo real
        n_sesiones_medicas=0,
        n_sesiones_psicologicas=0,
        n_sesiones_ampliacion=0,
        reintegro_parcial=reintegro_parcial,
        fecha_reintegro_parcial=rei.fecha_reintegro if rei else None,
        reintegro_total=reintegro_total,
        fecha_reintegro_total=None,                # campo no existe en el modelo real
    )

    # §7.5.4 Cierre
    # alta_terapeutica se deduce de CasoReintegro.tipo_alta == "terapeutica"
    alta_medica = bool(rei and rei.alta_medica)
    alta_psicologica = bool(rei and rei.alta_psicologica)
    alta_terapeutica = bool(rei and rei.tipo_alta == "terapeutica")
    fecha_alta_medica = rei.fecha_alta_medica if (rei and rei.alta_medica) else None
    fecha_alta_psicologica = rei.fecha_alta_psico if (rei and rei.alta_psicologica) else None

    cierre = SeccionCierreRead(
        alta_medica=alta_medica,
        fecha_alta_medica=fecha_alta_medica,
        alta_psicologica=alta_psicologica,
        fecha_alta_psicologica=fecha_alta_psicologica,
        alta_terapeutica=alta_terapeutica,
        fecha_alta_terapeutica=None,               # no existe como campo directo
        estado_general=ingreso.estado if ingreso.estado in ("cerrado", "derivado") else None,
        observaciones=rei.observaciones if rei else None,
    )

    return CasoConsolidadoRead(
        ingreso_id=ingreso.id,
        datos_caso=datos_caso,
        evaluaciones=evaluaciones,
        controles=controles,
        cierre=cierre,
    )


def generar_reporte(db: Session, filtros: FiltrosReporte) -> ReporteAuditoriaRead:
    """Genera el reporte de auditoría aplicando todos los filtros (AND).

    Cada fila es trazable por folio + número de siniestro (CA-3, RN-3).
    Un reporte vacío es válido (CA-4, TC-051-04).
    El período es siempre obligatorio y se aplica sobre fecha_ingreso del ingreso.

    Mapeo de filtros:
    - filtros.estado_caso → Ingreso.estado
    - filtros.tipo_ingreso → Ingreso.tipo_ingreso
    - filtros.tipo_denuncia → Ingreso.tipo_derivacion
    - filtros.region → Paciente.region
    - filtros.programa → Seguimiento.programa
    """
    condiciones = [
        Ingreso.fecha_ingreso >= filtros.fecha_desde,
        Ingreso.fecha_ingreso <= filtros.fecha_hasta,
    ]

    if filtros.estado_caso:
        condiciones.append(Ingreso.estado == filtros.estado_caso)
    if filtros.tipo_ingreso:
        condiciones.append(Ingreso.tipo_ingreso == filtros.tipo_ingreso)
    if filtros.tipo_denuncia:
        condiciones.append(Ingreso.tipo_derivacion == filtros.tipo_denuncia)
    if filtros.region:
        condiciones.append(Paciente.region == filtros.region)

    stmt = (
        select(Ingreso, Paciente, Seguimiento)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .outerjoin(Seguimiento, Seguimiento.ingreso_id == Ingreso.id)
        .where(and_(*condiciones))
        .order_by(Ingreso.fecha_ingreso, Ingreso.id)
    )

    # Filtro por programa (post-consulta sobre Seguimiento)
    if filtros.programa:
        stmt = stmt.where(Seguimiento.programa == filtros.programa)

    filas: list[FilaReporteRead] = []
    for ingreso, paciente, seg in db.execute(stmt):
        # Filtro post-consulta sobre campos de seguimiento (tipo_alta)
        if filtros.tipo_alta:
            rei: CasoReintegro | None = db.scalar(
                select(CasoReintegro).where(CasoReintegro.ingreso_id == ingreso.id)
            )
            tiene_alta = False
            if rei:
                if filtros.tipo_alta == "medica" and rei.alta_medica:
                    tiene_alta = True
                elif filtros.tipo_alta == "psicologica" and rei.alta_psicologica:
                    tiene_alta = True
                elif filtros.tipo_alta == "terapeutica" and rei.tipo_alta == "terapeutica":
                    tiene_alta = True
            if not tiene_alta:
                continue

        # profesional: médico de la última evaluación
        profesional: str | None = None
        if seg:
            profesional = seg.eval_medica_medico or seg.eval_psico_psicologo

        fila = FilaReporteRead(
            ingreso_id=ingreso.id,
            folio=ingreso.folio,
            numero_siniestro=ingreso.numero_siniestro,
            rut=paciente.rut,
            nombre_completo=paciente.nombre,
            region=paciente.region,
            fecha_denuncia=ingreso.fecha_ingreso,        # mapeado
            tipo_denuncia=ingreso.tipo_derivacion,       # mapeado
            estado_caso=ingreso.estado,                  # mapeado
            diagnostico_inicial=ingreso.diagnostico,
            diagnostico_post_reca=seg.reca_ep_ec if seg else None,
            profesional=profesional,
            fecha_calificacion_reca=None,                # no existe en el modelo real
            reintegro_parcial=False,                     # simplificado: no hay flag directo
            reintegro_total=False,                       # simplificado: no hay flag directo
            alta_medica=False,                           # se consulta vía CasoReintegro en get_caso
            alta_psicologica=False,
            alta_terapeutica=False,
        )
        filas.append(fila)

    return ReporteAuditoriaRead(
        filtros_aplicados=filtros,
        total=len(filas),
        filas=filas,
    )
