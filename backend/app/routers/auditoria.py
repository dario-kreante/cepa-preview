"""Router de Auditoría (EPIC-05).

Expone la vista consolidada del caso (CEPA-050) y los reportes de auditoría (CEPA-051).
Solo lectura: perfiles Coordinacion y Auditor; Administrativo solo con el permiso extra
«Acceso a Auditoría» (RN-2, D1, CA-012).
Todo acceso se registra en el log de auditoría (RN-7).

Nota sobre action="READ": el docstring de record_audit menciona {CREATE, UPDATE, DELETE,
LOGIN, LOGIN_FALLIDO, BLOQUEO} pero el campo es String libre, por lo que "READ" es válido
(no hay enum de BD). Si en el futuro se restringe el enum, cambiar a "CREATE" con prefijo.
"""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_auditoria
from app.db.session import get_db
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.schemas.auditoria import (
    CasoConsolidadoRead,
    FiltrosReporte,
    ReporteAuditoriaRead,
)
from app.services.auditoria import generar_reporte, get_caso_consolidado
from app.services.busqueda import buscar_pacientes
from app.services.excel import XLSX, planilla

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])

# Coordinacion y Auditor acceden al módulo de auditoría (RN-2, D1); un Administrativo solo
# con el permiso extra «Acceso a Auditoría» (CA-012, QA 23-11-2026).
_reader = Depends(require_auditoria)

# Prefijos que pueden usarse como fórmulas en ataques de inyección CSV (M1)
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@")


def _sanitize_csv_cell(value: str) -> str:
    """Prefija con ' cualquier celda string que comience con un carácter de fórmula (M1)."""
    if value and value[0] in _CSV_INJECTION_PREFIXES:
        return f"'{value}"
    return value


# ── CEPA-050: Vista consolidada del caso ──────────────────────────────────

@router.get(
    "/casos/{ingreso_id}",
    response_model=CasoConsolidadoRead,
    summary="Vista consolidada de un caso por ingreso_id (§7.5.1–§7.5.4)",
)
def ver_caso_consolidado(
    ingreso_id: int,
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> CasoConsolidadoRead:
    """Retorna todos los hitos del caso: datos, evaluaciones, controles y cierre.

    Solo lectura (CA-4, RN-1, RN-2). El acceso se registra en el log (RN-7).
    404 si el ingreso no existe.
    """
    caso = get_caso_consolidado(db, ingreso_id)
    if caso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso no encontrado.")

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_caso",
        entity_id=str(ingreso_id),
    )
    db.commit()  # C1: persistir la traza READ
    return caso


@router.get(
    "/casos",
    response_model=list[CasoConsolidadoRead],
    summary="Búsqueda de casos por texto libre (RUT, nombre, folio o siniestro)",
)
def buscar_casos(
    q: str | None = Query(
        default=None,
        description="Texto libre: RUT (con o sin formato), nombre parcial, folio o N° de siniestro",
    ),
    rut: str | None = Query(default=None, description="RUT normalizado del paciente"),
    folio: str | None = Query(default=None, description="Folio del ingreso"),
    numero_siniestro: str | None = Query(default=None, description="Número de siniestro"),
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> list[CasoConsolidadoRead]:
    """Busca casos por texto libre (``q``) o por RUT, folio o número de siniestro exactos.
    Retorna lista de vistas consolidadas.

    ``q`` reutiliza la búsqueda de pacientes (RUT normalizado, nombre parcial, folio,
    identidad SALUTEM) y además matchea el número de siniestro.

    Cada siniestro bajo el mismo RUT es un caso diferenciado (CA-2, RN-3, D2).
    """
    stmt = (
        select(Ingreso)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .order_by(Ingreso.fecha_ingreso.desc(), Ingreso.id.desc())
    )
    if q and q.strip():
        termino = q.strip()
        pacientes = [p.id for p in buscar_pacientes(db, termino)]
        stmt = stmt.where(
            or_(Ingreso.paciente_id.in_(pacientes), Ingreso.numero_siniestro == termino)
        )
    if rut:
        stmt = stmt.where(Paciente.rut == rut)
    if folio:
        stmt = stmt.where(Ingreso.folio == folio)
    if numero_siniestro:
        stmt = stmt.where(Ingreso.numero_siniestro == numero_siniestro)

    ingresos = list(db.scalars(stmt))

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_busqueda",
        # entity_id es String(60): solo los criterios usados, recortado.
        entity_id="&".join(
            f"{k}={v}"
            for k, v in (("q", q), ("rut", rut), ("folio", folio), ("siniestro", numero_siniestro))
            if v
        )[:60],
    )
    db.commit()  # C1: persistir la traza READ

    resultados: list[CasoConsolidadoRead] = []
    for ing in ingresos:
        caso = get_caso_consolidado(db, ing.id)
        if caso is not None:
            resultados.append(caso)
    return resultados


# ── CEPA-051: Reportes de auditoría ───────────────────────────────────────

@router.post(
    "/reportes",
    response_model=ReporteAuditoriaRead,
    summary="Genera reporte de auditoría con filtros combinables (AND)",
)
def generar_reporte_auditoria(
    filtros: FiltrosReporte,
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> ReporteAuditoriaRead:
    """Genera un reporte de auditoría filtrando por período, diagnóstico, profesional
    y estado del caso. El período (fecha_desde, fecha_hasta) es obligatorio (RN-2).
    Un resultado vacío es válido (CA-4). La generación se registra en el log (RN-5).
    """
    reporte = generar_reporte(db, filtros)

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_reporte",
        entity_id=(
            f"{filtros.fecha_desde}..{filtros.fecha_hasta}"
            f"|estado={filtros.estado_caso}|dx={filtros.diagnostico}"
        ),
    )
    db.commit()  # C1: persistir la traza READ
    return reporte


@router.post(
    "/reportes/descargar",
    summary="Descarga el reporte de auditoría en Excel (.xlsx)",
)
def descargar_reporte_csv(
    filtros: FiltrosReporte,
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> Response:
    """Descarga el reporte de auditoría como planilla Excel.

    QA-005 (23-11-2026): antes era un CSV que Excel abría en una sola columna y con las
    tildes rotas. Las columnas incluyen folio, N° de siniestro e ID de ingreso para
    trazabilidad (CA-2, CA-3, RN-3, RN-4, TC-051-02, TC-051-03).
    """
    reporte = generar_reporte(db, filtros)

    record_audit(
        db,
        actor=current_user.username,
        action="READ",
        entity="auditoria_descarga_csv",
        entity_id=f"{filtros.fecha_desde}..{filtros.fecha_hasta}|total={reporte.total}",
    )
    db.commit()  # C1: persistir la traza READ

    contenido = planilla(
        "Reporte de auditoría",
        ENCABEZADOS_REPORTE,
        (
            [
                fila.ingreso_id, fila.folio, fila.numero_siniestro, fila.rut,
                fila.nombre_completo, fila.region, fila.tipo_ingreso, fila.programa,
                fila.convenio, fila.fecha_denuncia, fila.tipo_denuncia,
                ESTADOS_CASO.get(fila.estado_caso or "", fila.estado_caso),
                fila.diagnostico_inicial, fila.diagnostico_post_reca, fila.profesional,
                fila.fecha_calificacion_reca, fila.reintegro_parcial, fila.reintegro_total,
                fila.alta_medica, fila.alta_psicologica, fila.alta_terapeutica,
            ]
            for fila in reporte.filas
        ),
        anchos=(10, 14, 16, 14, 32, 16, 18, 18, 26, 14, 18, 14, 30, 30, 26, 14, 12, 12, 12, 12, 12),
    )
    nombre_archivo = f"reporte_auditoria_{filtros.fecha_desde}_{filtros.fecha_hasta}.xlsx"
    return Response(
        content=contenido,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


ENCABEZADOS_REPORTE = (
    "ID ingreso", "Folio", "N° siniestro", "RUT", "Nombre", "Región", "Tipo de ingreso",
    "Programa", "Convenio", "Fecha denuncia", "Tipo de denuncia", "Estado del caso",
    "Diagnóstico inicial", "Diagnóstico post RECA", "Profesional", "Fecha calificación RECA",
    "Reintegro parcial", "Reintegro total", "Alta médica", "Alta psicológica", "Alta terapéutica",
)
ESTADOS_CASO = {"activo": "Activo", "cerrado": "Cerrado", "derivado": "Derivado", "encuadre": "En encuadre"}
