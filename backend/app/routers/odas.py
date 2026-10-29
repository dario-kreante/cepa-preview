import json

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.oda import (
    OdaAlerta,
    OdaCreate,
    OdaImportError,
    OdaImportFilaSinPaciente,
    OdaImportPorVencer,
    OdaImportResumen,
    OdaRead,
)
from app.services.oda import listar_odas, odas_por_vencer, registrar_oda
from app.services.oda_importacion import ArchivoInvalidoError, importar_reporte

router = APIRouter(prefix="/api/v1", tags=["odas"])

MAX_XLSX_BYTES = 10 * 1024 * 1024  # 10 MB

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "/ingresos/{ingreso_id}/odas",
    response_model=OdaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_oda(
    ingreso_id: int,
    payload: OdaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OdaRead:
    oda = registrar_oda(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="oda", entity_id=str(oda.id)
    )
    db.commit()
    db.refresh(oda)
    return oda


@router.get(
    "/ingresos/{ingreso_id}/odas",
    response_model=list[OdaRead],
    dependencies=[Depends(_reader)],
)
def listar(ingreso_id: int, db: Session = Depends(get_db)) -> list[OdaRead]:
    return listar_odas(db, ingreso_id)


@router.post(
    "/odas/importar",
    response_model=OdaImportResumen,
    dependencies=[Depends(_writer)],
)
async def importar(
    file: UploadFile,
    dry_run: bool = Query(False, description="true = previsualizar sin guardar"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OdaImportResumen:
    """Carga el «Reporte Prestador» del portal ISL (xlsx ≤ 10 MB) y actualiza las ODAS.

    Idempotente: subir la misma planilla dos veces no duplica. Con ``dry_run=true`` aplica
    los cambios dentro de un savepoint, arma el resumen y lo revierte (previsualización).
    """
    nombre = file.filename or ""
    if not nombre.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="El archivo debe ser un Excel .xlsx (Reporte Prestador del portal ISL).",
        )
    contenido = await file.read(MAX_XLSX_BYTES + 1)
    if len(contenido) > MAX_XLSX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="El archivo supera el máximo de 10 MB.",
        )

    savepoint = db.begin_nested()
    try:
        # El parseo y el upsert son síncronos y pueden tardar: fuera del event loop.
        resumen = await run_in_threadpool(importar_reporte, db, contenido)
    except ArchivoInvalidoError as exc:
        savepoint.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    respuesta = OdaImportResumen(
        dry_run=dry_run,
        archivo=nombre,
        filas_leidas=resumen.filas_leidas,
        creadas=resumen.creadas,
        actualizadas=resumen.actualizadas,
        sin_cambios=resumen.sin_cambios,
        match_por_siniestro=resumen.match_por_siniestro,
        match_por_rut=resumen.match_por_rut,
        sin_paciente=[OdaImportFilaSinPaciente(**vars(f)) for f in resumen.sin_paciente],
        errores=[OdaImportError(**vars(e)) for e in resumen.errores],
        ventana_dias=resumen.ventana_dias,
        por_vencer_paciente_activo=len(resumen.por_vencer_paciente_activo),
        por_vencer=[OdaImportPorVencer(**vars(p)) for p in resumen.por_vencer_paciente_activo],
    )
    if dry_run:
        savepoint.rollback()
        return respuesta

    for oda, accion in resumen.cambios:
        record_audit(
            db,
            actor=current_user.username,
            action=accion,
            entity="oda",
            entity_id=str(oda.id),
            valor_nuevo=json.dumps(
                {
                    "origen": "reporte_isl",
                    "identificador": oda.identificador,
                    "ingreso_id": oda.ingreso_id,
                    "fecha_vencimiento": oda.fecha_vencimiento.isoformat(),
                }
            ),
        )
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="oda_importacion",
        entity_id=nombre[:60] or None,
        valor_nuevo=json.dumps(
            {
                "filas_leidas": respuesta.filas_leidas,
                "creadas": respuesta.creadas,
                "actualizadas": respuesta.actualizadas,
                "sin_cambios": respuesta.sin_cambios,
                "sin_paciente": len(respuesta.sin_paciente),
                "errores": len(respuesta.errores),
                "por_vencer_paciente_activo": respuesta.por_vencer_paciente_activo,
            }
        ),
    )
    savepoint.commit()
    db.commit()
    return respuesta


@router.get("/odas/alertas", response_model=list[OdaAlerta], dependencies=[Depends(_reader)])
def alertas(db: Session = Depends(get_db)) -> list[OdaAlerta]:
    return odas_por_vencer(db)
