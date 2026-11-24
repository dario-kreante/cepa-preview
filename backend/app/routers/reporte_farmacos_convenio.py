"""Reporte «Externalizado» de fármacos (QA-010 / QA-013): cada fármaco recetado en el período,
clasificado frente a la canasta del Convenio 002 y la lista Externalizado
(``app.services.reporte_farmacos_convenio``). Lectores: Coordinación y Administrativo.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.routers.reporte_ambulatorio import Desde, Hasta, _excel, _validar_rango
from app.schemas.reportes_ambulatorio_externalizado import (
    FarmacoConvenioItem,
    ReporteFarmacosConvenioResponse,
    ResumenClasificacion,
)
from app.services import reporte_farmacos_convenio

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector_farmacos = require_role("Coordinacion", "Administrativo")

_CLASIFICACIONES = ("Convenio 002", "Convenio 001", "REVISAR", "Fuera de convenio")


@router.get("/farmacos-convenio", response_model=ReporteFarmacosConvenioResponse)
def get_farmacos_convenio(
    fecha_desde: Desde,
    fecha_hasta: Hasta,
    paciente_id: int | None = Query(None, description="Solo los fármacos de este paciente"),
    db: Session = Depends(get_db),
    current_user=Depends(_lector_farmacos),
) -> ReporteFarmacosConvenioResponse:
    _validar_rango(fecha_desde, fecha_hasta)
    filas = reporte_farmacos_convenio.construir_filas(
        db, fecha_desde, fecha_hasta, paciente_id=paciente_id
    )
    conteo = Counter(f.clasificacion for f in filas)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="reporte_farmacos_convenio",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )
    db.commit()
    return ReporteFarmacosConvenioResponse(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total=len(filas),
        resumen=[ResumenClasificacion(clasificacion=c, total=conteo.get(c, 0)) for c in _CLASIFICACIONES],
        items=[FarmacoConvenioItem(**vars(f)) for f in filas],
    )


@router.get("/farmacos-convenio/excel")
def get_farmacos_convenio_excel(
    fecha_desde: Desde,
    fecha_hasta: Hasta,
    paciente_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector_farmacos),
) -> Response:
    _validar_rango(fecha_desde, fecha_hasta)
    filas = reporte_farmacos_convenio.construir_filas(
        db, fecha_desde, fecha_hasta, paciente_id=paciente_id
    )
    contenido = reporte_farmacos_convenio.generar_excel(filas)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="reporte_farmacos_convenio_excel",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )
    db.commit()
    return _excel(
        contenido, f"externalizado-{fecha_desde.isoformat()}-{fecha_hasta.isoformat()}.xlsx"
    )
