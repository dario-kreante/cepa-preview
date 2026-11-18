"""QA-004 — Reporte de ingresos del período.

Una fila por ingreso (nombre, RUT, folio, tipo de ingreso, programa, región) más los
pacientes creados en SALUTEM que siguen pendientes de folio (`estado_registro ==
"pendiente_folio"`), marcados como pendientes. El período usa `fecha_ingreso` para los
ingresos y la fecha de creación del borrador (hora de Chile) para los pendientes.

Sin doble conteo: un pendiente que ya tiene un ingreso dentro del período se cuenta solo
por ese ingreso. Los totales por tipo de ingreso, región, programa y convenio incluyen a
los pendientes bajo etiquetas propias («Pendiente de folio», «Sin región»…).
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.domain.enums import EstadoRegistroPaciente
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.schemas.reporte_ingresos import (
    ConteoIngreso,
    IngresoReporteItem,
    ReporteIngresosResponse,
)

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")

PERIODO_DEFECTO_DIAS = 30
_SANTIAGO = ZoneInfo("America/Santiago")
ETIQUETA_PENDIENTE = "Pendiente de folio"


def _consulta_ingresos(desde: date, hasta: date):
    return (
        select(Ingreso, Paciente)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .where(Ingreso.fecha_ingreso >= desde, Ingreso.fecha_ingreso <= hasta)
    )


def _limites_utc(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """[inicio, fin) del período en hora de Chile, como instantes con zona."""
    inicio = datetime.combine(desde, time.min, tzinfo=_SANTIAGO)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=_SANTIAGO)
    return inicio, fin


def _consulta_pendientes(desde: date, hasta: date):
    inicio, fin = _limites_utc(desde, hasta)
    con_ingreso_en_periodo = exists().where(
        Ingreso.paciente_id == Paciente.id,
        Ingreso.fecha_ingreso >= desde,
        Ingreso.fecha_ingreso <= hasta,
    )
    return select(Paciente).where(
        Paciente.estado_registro == EstadoRegistroPaciente.PENDIENTE_FOLIO.value,
        Paciente.created_at >= inicio,
        Paciente.created_at < fin,
        ~con_ingreso_en_periodo,
    )


def _ranking(contador: Counter[str]) -> list[ConteoIngreso]:
    return [
        ConteoIngreso(etiqueta=k, total=v)
        for k, v in sorted(contador.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


@router.get("/ingresos", response_model=ReporteIngresosResponse)
def get_reporte_ingresos(
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(_lector),
) -> ReporteIngresosResponse:
    hasta = fecha_hasta or date.today()
    desde = fecha_desde or (hasta - timedelta(days=PERIODO_DEFECTO_DIAS - 1))
    if desde > hasta:
        raise HTTPException(
            status_code=422,
            detail="La fecha «desde» no puede ser posterior a «hasta».",
        )

    items: list[IngresoReporteItem] = []
    for ing, pac in db.execute(_consulta_ingresos(desde, hasta)).all():
        items.append(
            IngresoReporteItem(
                paciente_id=pac.id,
                ingreso_id=ing.id,
                paciente_nombre=pac.nombre,
                paciente_rut=pac.rut,
                folio=ing.folio,
                pendiente=False,
                tipo_ingreso=ing.tipo_ingreso,
                programa=ing.programa,
                region=pac.region,
                tipo_convenio=ing.tipo_convenio,
                fecha=ing.fecha_ingreso,
            )
        )
    for pac in db.execute(_consulta_pendientes(desde, hasta)).scalars().all():
        creado = pac.created_at
        if creado.tzinfo is None:  # Oracle/SQLite pueden devolverlo sin zona (UTC)
            creado = creado.replace(tzinfo=ZoneInfo("UTC"))
        items.append(
            IngresoReporteItem(
                paciente_id=pac.id,
                paciente_nombre=pac.nombre,
                paciente_rut=pac.rut,
                pendiente=True,
                region=pac.region,
                fecha=creado.astimezone(_SANTIAGO).date(),
            )
        )
    items.sort(key=lambda i: (i.fecha, i.paciente_id), reverse=True)

    tipos: Counter[str] = Counter()
    regiones: Counter[str] = Counter()
    programas: Counter[str] = Counter()
    convenios: Counter[str] = Counter()
    for i in items:
        tipos[ETIQUETA_PENDIENTE if i.pendiente else (i.tipo_ingreso or "Sin tipo")] += 1
        regiones[(i.region or "").strip() or "Sin región"] += 1
        programas[(i.programa or "").strip() or "Sin programa"] += 1
        convenios[(i.tipo_convenio or "").strip() or "Sin convenio"] += 1

    pendientes = sum(1 for i in items if i.pendiente)

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reporte_ingresos",
        entity_id=f"{desde}..{hasta}",
    )
    db.commit()

    return ReporteIngresosResponse(
        periodo_desde=desde,
        periodo_hasta=hasta,
        total=len(items),
        total_con_folio=len(items) - pendientes,
        total_pendientes=pendientes,
        por_tipo_ingreso=_ranking(tipos),
        por_region=_ranking(regiones),
        por_programa=_ranking(programas),
        por_convenio=_ranking(convenios),
        items=items,
    )
