"""CEPA-097 — Reporte de ODAS vencidas (D3).

RN-1: vencida = fecha_vencimiento < fecha actual (estricto menor, NO <=).
Solo cuentan las ODA vigentes (no reemplazadas por una carga ISL posterior) de
casos activos: es el mismo universo que la tarjeta «ODA vencidas» del dashboard.
RN-2: las ODAS son manuales y tienen fecha_vencimiento (D3).
Deviación: modelo Oda (no ODA); fecha_registro nullable añadida EPIC-09 migración 09000.

DD-6 (EPIC-09 rework): se popula ODAVencidaItem.programa/region/comuna con datos
del Ingreso y Paciente (join ya disponible). También se incluye folio/nombre paciente
por CA-1.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.reportes import (
    ODAEstadoItem,
    ODAVencidaItem,
    OrdenCobertura,
    ReporteODAEstadoResponse,
    ReporteODASVencidasResponse,
)
from app.services.dashboard_operativo import DIAS_ODA_POR_VENCER
from app.services.reporte_odas import (
    FilaVencida,
    construir_filas_vencidas,
    generar_excel,
    listar_estado_odas,
)

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _item(f: FilaVencida) -> ODAVencidaItem:
    o = f.oda  # None = atendido sin ODA: los campos propios de la orden van vacíos
    return ODAVencidaItem(
        id=o.id if o else None,
        folio_id=f.ingreso.id,
        identificador=o.identificador if o else None,
        folio=f.ingreso.folio,
        paciente_nombre=f.paciente.nombre,
        paciente_rut=f.paciente.rut,
        fecha_registro=o.fecha_registro if o else None,
        fecha_vencimiento=o.fecha_vencimiento if o else None,
        programa=f.ingreso.programa,
        region=f.paciente.region,
        comuna=f.paciente.comuna,
        ordenes=[
            OrdenCobertura(
                identificador=x.identificador,
                tipo=x.tipo,
                fecha_inicio=x.fecha_inicio,
                fecha_termino=x.fecha_termino,
            )
            for x in f.ordenes
        ],
        fechas_atencion=f.fechas_atencion,
        cobertura=f.cobertura,
        estado_gestion=o.estado_gestion if o else None,
    )


@router.get("/odas-vencidas", response_model=ReporteODASVencidasResponse)
def get_odas_vencidas(
    programa: str | None = Query(
        None, description="regular | ley_karin | pipt (otro valor: coincidencia exacta)"
    ),
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteODASVencidasResponse:
    """CA-1..CA-3: ODAS vigentes de casos activos con fecha_vencimiento < hoy (estricto).

    TC-097-02: ODA que vence exactamente hoy NO aparece (condición estricta < hoy).
    QA-007: una fila por paciente, con el cruce de cobertura y el estado de gestión.
    También incluye a los atendidos sin ninguna ODA (SOLICITAR, sin gestión).
    """

    # Fecha operacional local (convención del resto del sistema: date.today();
    # usar UTC adelanta el día desde las 20-21h hora de Chile y rompe RN-1).
    hoy = date.today()
    filas = construir_filas_vencidas(db, hoy, programa=programa, region=region, comuna=comuna)
    items = [_item(f) for f in filas]

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_odas_vencidas",
        entity_id=str(hoy),
    )
    db.commit()

    return ReporteODASVencidasResponse(fecha_consulta=hoy, total=len(items), items=items)


@router.get("/odas-vencidas/excel")
def get_odas_vencidas_excel(
    programa: str | None = Query(None),
    region: str | None = Query(None),
    comuna: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> Response:
    """QA-007: la tabla de ODA vencidas en Excel (mismos filtros que el JSON)."""
    hoy = date.today()
    filas = construir_filas_vencidas(db, hoy, programa=programa, region=region, comuna=comuna)
    contenido = generar_excel(filas)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_odas_vencidas_excel",
        entity_id=str(hoy),
    )
    db.commit()
    return Response(
        content=contenido,
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="odas-vencidas-{hoy.isoformat()}.xlsx"'},
    )


@router.get("/odas-estado", response_model=ReporteODAEstadoResponse)
def get_odas_estado(
    estado_caso: str | None = Query(None, description="activo | cerrado | encuadre | derivado"),
    programa: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteODAEstadoResponse:
    """QA-006: estado de la ODA de cada paciente, sin abrir ficha por ficha."""
    hoy = date.today()
    filas = listar_estado_odas(db, hoy, estado_caso=estado_caso, programa=programa)
    items = [
        ODAEstadoItem(
            ingreso_id=f.ingreso.id,
            folio=f.ingreso.folio,
            paciente_nombre=f.paciente.nombre,
            paciente_rut=f.paciente.rut,
            fecha_ingreso=f.ingreso.fecha_ingreso,
            estado_caso=f.ingreso.estado,
            programa=f.ingreso.programa,
            estado_oda=f.estado_oda,
            fecha_vencimiento=f.oda.fecha_vencimiento if f.oda else None,
            dias_para_vencer=f.dias_para_vencer,
        )
        for f in filas
    ]
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_odas_estado",
        entity_id=str(hoy),
    )
    db.commit()
    return ReporteODAEstadoResponse(
        fecha_consulta=hoy, total=len(items), dias_por_vencer=DIAS_ODA_POR_VENCER, items=items
    )
