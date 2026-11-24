"""Reporte «Ambulatorio» (QA del 23-11-2026): atenciones realizadas en el formato de la
plataforma ISL, con región, comuna y sus códigos CUT (``app.services.reporte_ambulatorio``).

Lectores: los mismos de los reportes de ODA. También define los helpers de rango y descarga que
usa el reporte «Externalizado».
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.reportes_ambulatorio_externalizado import (
    AmbulatorioItem,
    ReporteAmbulatorioResponse,
)
from app.services import reporte_ambulatorio
from app.services.excel import XLSX

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

# Mismos lectores que los reportes de ODA.
_lector_ambulatorio = require_role("Coordinacion", "Auditor", "Administrativo")

Desde = Annotated[date, Query(description="Inicio del período (obligatorio)")]
Hasta = Annotated[date, Query(description="Fin del período, inclusive (obligatorio)")]


def _validar_rango(desde: date, hasta: date) -> None:
    if desde > hasta:
        raise HTTPException(
            422, "La fecha desde no puede ser posterior a la fecha hasta."
        )


def _excel(contenido: bytes, nombre: str) -> Response:
    return Response(
        content=contenido,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


# ── Ambulatorio ────────────────────────────────────────────────────────────────


@router.get("/ambulatorio", response_model=ReporteAmbulatorioResponse)
def get_ambulatorio(
    fecha_desde: Desde,
    fecha_hasta: Hasta,
    programa: str | None = Query(
        None, description="regular | ingreso_isl | tratamiento_isl | ley_karin | pipt (otro valor: coincidencia exacta)"
    ),
    region: str | None = Query(None, description="Región del paciente (lista de SIGE)"),
    db: Session = Depends(get_db),
    current_user=Depends(_lector_ambulatorio),
) -> ReporteAmbulatorioResponse:
    _validar_rango(fecha_desde, fecha_hasta)
    filas = reporte_ambulatorio.construir_filas(
        db, fecha_desde, fecha_hasta, programa=programa, region=region
    )
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="reporte_ambulatorio",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )
    db.commit()
    return ReporteAmbulatorioResponse(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total=len(filas),
        items=[AmbulatorioItem(**vars(f)) for f in filas],
    )


@router.get("/ambulatorio/excel")
def get_ambulatorio_excel(
    fecha_desde: Desde,
    fecha_hasta: Hasta,
    programa: str | None = Query(None),
    region: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector_ambulatorio),
) -> Response:
    _validar_rango(fecha_desde, fecha_hasta)
    filas = reporte_ambulatorio.construir_filas(
        db, fecha_desde, fecha_hasta, programa=programa, region=region
    )
    contenido = reporte_ambulatorio.generar_excel(filas)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="reporte_ambulatorio_excel",
        entity_id=f"{fecha_desde}/{fecha_hasta}",
    )
    db.commit()
    return _excel(contenido, f"ambulatorio-{fecha_desde.isoformat()}-{fecha_hasta.isoformat()}.xlsx")
