"""Router de Auditoría (EPIC-05).

Expone la vista consolidada del caso (CEPA-050) y los reportes de auditoría (CEPA-051).
Solo lectura: perfiles Coordinacion y Auditor; Administrativo sin acceso (RN-2, D1).
Todo acceso se registra en el log de auditoría (RN-7).

Nota sobre action="READ": el docstring de record_audit menciona {CREATE, UPDATE, DELETE,
LOGIN, LOGIN_FALLIDO, BLOQUEO} pero el campo es String libre, por lo que "READ" es válido
(no hay enum de BD). Si en el futuro se restringe el enum, cambiar a "CREATE" con prefijo.
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.schemas.auditoria import (
    CasoConsolidadoRead,
    FiltrosReporte,
    ReporteAuditoriaRead,
)
from app.services.auditoria import generar_reporte, get_caso_consolidado

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])

# Solo Coordinacion y Auditor acceden al módulo de auditoría (RN-2, D1)
_reader = Depends(require_role("Coordinacion", "Auditor"))

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
    summary="Búsqueda de casos por RUT o folio",
)
def buscar_casos(
    rut: str | None = Query(default=None, description="RUT normalizado del paciente"),
    folio: str | None = Query(default=None, description="Folio del ingreso"),
    numero_siniestro: str | None = Query(default=None, description="Número de siniestro"),
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> list[CasoConsolidadoRead]:
    """Busca casos por RUT, folio o número de siniestro. Retorna lista de vistas consolidadas.

    Cada siniestro bajo el mismo RUT es un caso diferenciado (CA-2, RN-3, D2).
    """
    stmt = (
        select(Ingreso)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .order_by(Ingreso.fecha_ingreso.desc(), Ingreso.id.desc())
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
        entity_id=f"rut={rut}&folio={folio}&siniestro={numero_siniestro}",
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
    summary="Descarga el reporte de auditoría en formato CSV",
)
def descargar_reporte_csv(
    filtros: FiltrosReporte,
    current_user=Depends(get_current_user),
    _: None = _reader,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Descarga el reporte de auditoría como archivo CSV.

    Los encabezados incluyen folio, numero_siniestro e ingreso_id para trazabilidad
    (CA-2, CA-3, RN-3, RN-4, TC-051-02, TC-051-03).
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

    output = io.StringIO()
    writer = csv.writer(output)

    # Encabezados (incluyen folio, numero_siniestro e ingreso_id para trazabilidad)
    encabezados = [
        "ingreso_id",
        "folio",
        "numero_siniestro",
        "rut",
        "nombre_completo",
        "region",
        "fecha_denuncia",
        "tipo_denuncia",
        "estado_caso",
        "diagnostico_inicial",
        "diagnostico_post_reca",
        "profesional",
        "fecha_calificacion_reca",
        "reintegro_parcial",
        "reintegro_total",
        "alta_medica",
        "alta_psicologica",
        "alta_terapeutica",
    ]
    writer.writerow(encabezados)

    for fila in reporte.filas:
        writer.writerow([
            fila.ingreso_id,
            _sanitize_csv_cell(fila.folio),
            _sanitize_csv_cell(fila.numero_siniestro or ""),
            _sanitize_csv_cell(fila.rut),
            _sanitize_csv_cell(fila.nombre_completo),
            _sanitize_csv_cell(fila.region or ""),
            fila.fecha_denuncia or "",
            _sanitize_csv_cell(fila.tipo_denuncia or ""),
            _sanitize_csv_cell(fila.estado_caso or ""),
            _sanitize_csv_cell(fila.diagnostico_inicial or ""),
            _sanitize_csv_cell(fila.diagnostico_post_reca or ""),
            _sanitize_csv_cell(fila.profesional or ""),
            fila.fecha_calificacion_reca or "",
            fila.reintegro_parcial,
            fila.reintegro_total,
            fila.alta_medica,
            fila.alta_psicologica,
            fila.alta_terapeutica,
        ])

    output.seek(0)
    nombre_archivo = (
        f"reporte_auditoria_{filtros.fecha_desde}_{filtros.fecha_hasta}.csv"
    )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )
