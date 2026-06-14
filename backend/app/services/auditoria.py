"""Servicio de agregación de auditoría (EPIC-05).

Solo lectura: agrega datos de los módulos fuente vía ORM portable (sin SQL específico
de motor). No modifica datos clínicos (RN-1, CA-4).

ADAPTACIONES respecto al plan original (declaradas):
- Seguimiento real: eval_medica_fecha / eval_psico_fecha (no fecha_eval_medica/psicologica).
  reca_ep_ec mapea a diagnostico_post_reca. Sin campos n_sesiones_*.
- Ingreso real: fecha_diep_diat (→ fecha_denuncia DTO, I3), fecha_ingreso (→ fecha_derivacion DTO, I3),
  tipo_derivacion (→ tipo_denuncia DTO), estado (→ estado_caso DTO). diagnostico mapea a diagnostico_inicial.
  programa vive en Seguimiento.programa.
- Reintegro real: modelo CasoReintegro (no Reintegro). Campos alta_medica, alta_psicologica,
  fecha_alta_psico (no fecha_alta_psicologica). alta_terapeutica se deduce de tipo_alta.
  estado_reintegro → EstadoReintegro.PARCIAL/TOTAL (I2).
- CasoReintegro no tiene FK directa a ingreso en la relación ORM del modelo Ingreso,
  por lo que se consulta directamente con where(ingreso_id == ...).
- numero_sesiones_evaluacion, n_sesiones_medicas/psicologicas/ampliacion: no existen
  en el modelo real → se retornan como None (S2).
- Reca.fecha_reca → fecha_calificacion_reca (M3).
- M2: alta_medica/psicologica/terapeutica y reintegro_* poblados desde CasoReintegro en reporte.
"""
from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.reintegro_enums import EstadoReintegro
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro, Reca
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
    - Ingreso.fecha_diep_diat → datos_caso.fecha_denuncia (I3: DIAT/DIEP IS the denuncia)
    - Ingreso.fecha_ingreso → datos_caso.fecha_derivacion (I3)
    - Ingreso.tipo_derivacion → datos_caso.tipo_denuncia
    - Ingreso.diagnostico → evaluaciones.diagnostico_inicial
    - Seguimiento.reca_ep_ec → evaluaciones.diagnostico_post_reca
    - Seguimiento.eval_medica_fecha → evaluaciones.fecha_eval_medica
    - Seguimiento.eval_psico_fecha → evaluaciones.fecha_eval_psicologica
    - Reca.fecha_reca → evaluaciones.fecha_calificacion_reca (M3)
    - CasoReintegro.estado_reintegro == PARCIAL/TOTAL → controles.reintegro_parcial/total (I2)
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

    # Reca (para fecha_calificacion_reca — M3)
    reca: Reca | None = None
    if rei is not None:
        reca = db.scalar(
            select(Reca).where(Reca.caso_reintegro_id == rei.id)
        )

    # §7.5.1 Datos del caso
    # I3: fecha_diep_diat IS the denuncia; fecha_ingreso is the derivacion date
    datos_caso = SeccionDatosCasoRead(
        folio=ingreso.folio,
        numero_siniestro=ingreso.numero_siniestro,
        fecha_denuncia=ingreso.fecha_diep_diat,      # I3: DIAT/DIEP date = denuncia
        tipo_denuncia=ingreso.tipo_derivacion,        # Ingreso.tipo_derivacion → DTO tipo_denuncia
        fecha_derivacion=ingreso.fecha_ingreso,       # I3: fecha_ingreso = fecha derivacion
        nombre_completo=paciente.nombre,
        rut=paciente.rut,
        region=paciente.region,
    )

    # §7.5.2 Evaluaciones
    # diagnostico_inicial: Ingreso.diagnostico (diagnóstico de ingreso)
    # diagnostico_post_reca: Seguimiento.reca_ep_ec (diagnóstico post-RECA)
    # numero_sesiones_evaluacion: no existe en el modelo real → None (S2)
    # fecha_calificacion_reca: Reca.fecha_reca (M3)
    evaluaciones = SeccionEvaluacionesRead(
        fecha_eval_medica=seg.eval_medica_fecha if seg else None,
        fecha_eval_psicologica=seg.eval_psico_fecha if seg else None,
        fecha_calificacion_reca=reca.fecha_reca if reca else None,   # M3
        diagnostico_inicial=ingreso.diagnostico,
        diagnostico_post_reca=seg.reca_ep_ec if seg else None,
        numero_sesiones_evaluacion=None,              # S2: no existe en el modelo real
    )

    # §7.5.3 Controles y tratamiento
    # n_sesiones_* no existen en los modelos reales → None (S2)
    # I2: usar EstadoReintegro en lugar de deducciones
    reintegro_parcial = bool(rei and rei.estado_reintegro == EstadoReintegro.PARCIAL)
    reintegro_total = bool(rei and rei.estado_reintegro == EstadoReintegro.TOTAL)
    # I2: fecha según estado
    fecha_reintegro_parcial = rei.fecha_reintegro if (rei and reintegro_parcial) else None
    fecha_reintegro_total = rei.fecha_reintegro if (rei and reintegro_total) else None
    controles = SeccionControlesRead(
        fecha_primera_consulta_medica=None,           # campo no existe en el modelo real
        fecha_primera_consulta_psicologica=None,      # campo no existe en el modelo real
        n_sesiones_medicas=None,                      # S2
        n_sesiones_psicologicas=None,                 # S2
        n_sesiones_ampliacion=None,                   # S2
        reintegro_parcial=reintegro_parcial,
        fecha_reintegro_parcial=fecha_reintegro_parcial,
        reintegro_total=reintegro_total,
        fecha_reintegro_total=fecha_reintegro_total,
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
    - filtros.diagnostico → OR(Ingreso.diagnostico, Seguimiento.reca_ep_ec) ilike (I1)
    - filtros.profesional → OR(Seguimiento.eval_medica_medico, Seguimiento.eval_psico_psicologo) ilike (I1)
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

    # Filtro por programa (sobre Seguimiento)
    if filtros.programa:
        stmt = stmt.where(Seguimiento.programa == filtros.programa)

    # I1: filtro diagnostico — OR case-insensitive substring sobre Ingreso.diagnostico y Seguimiento.reca_ep_ec
    if filtros.diagnostico:
        patron = f"%{filtros.diagnostico}%"
        stmt = stmt.where(
            or_(
                Ingreso.diagnostico.ilike(patron),
                Seguimiento.reca_ep_ec.ilike(patron),
            )
        )

    # I1: filtro profesional — OR case-insensitive substring sobre eval_medica_medico / eval_psico_psicologo
    if filtros.profesional:
        patron_prof = f"%{filtros.profesional}%"
        stmt = stmt.where(
            or_(
                Seguimiento.eval_medica_medico.ilike(patron_prof),
                Seguimiento.eval_psico_psicologo.ilike(patron_prof),
            )
        )

    filas: list[FilaReporteRead] = []
    for ingreso, paciente, seg in db.execute(stmt):
        # CasoReintegro para M2 (altas), I2 (EstadoReintegro), tipo_alta filter
        rei: CasoReintegro | None = db.scalar(
            select(CasoReintegro).where(CasoReintegro.ingreso_id == ingreso.id)
        )

        # Filtro post-consulta sobre tipo_alta
        if filtros.tipo_alta:
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

        # M3: fecha_calificacion_reca desde Reca
        fecha_calificacion_reca = None
        if rei is not None:
            reca: Reca | None = db.scalar(
                select(Reca).where(Reca.caso_reintegro_id == rei.id)
            )
            if reca is not None:
                fecha_calificacion_reca = reca.fecha_reca

        # I2: usar EstadoReintegro para reintegro_parcial/total
        reintegro_parcial = bool(rei and rei.estado_reintegro == EstadoReintegro.PARCIAL)
        reintegro_total = bool(rei and rei.estado_reintegro == EstadoReintegro.TOTAL)

        # M2: poblar altas desde CasoReintegro
        alta_medica = bool(rei and rei.alta_medica)
        alta_psicologica = bool(rei and rei.alta_psicologica)
        alta_terapeutica = bool(rei and rei.tipo_alta == "terapeutica")

        fila = FilaReporteRead(
            ingreso_id=ingreso.id,
            folio=ingreso.folio,
            numero_siniestro=ingreso.numero_siniestro,
            rut=paciente.rut,
            nombre_completo=paciente.nombre,
            region=paciente.region,
            fecha_denuncia=ingreso.fecha_diep_diat,      # I3: DIAT/DIEP date = denuncia
            tipo_denuncia=ingreso.tipo_derivacion,
            estado_caso=ingreso.estado,
            diagnostico_inicial=ingreso.diagnostico,
            diagnostico_post_reca=seg.reca_ep_ec if seg else None,
            profesional=profesional,
            fecha_calificacion_reca=fecha_calificacion_reca,  # M3
            reintegro_parcial=reintegro_parcial,              # I2
            reintegro_total=reintegro_total,                  # I2
            alta_medica=alta_medica,                          # M2
            alta_psicologica=alta_psicologica,                # M2
            alta_terapeutica=alta_terapeutica,                # M2
        )
        filas.append(fila)

    return ReporteAuditoriaRead(
        filtros_aplicados=filtros,
        total=len(filas),
        filas=filas,
    )
