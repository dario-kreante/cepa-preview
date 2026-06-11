"""CEPA-096 — Ventanas de visualización por proceso (§7.10, P1).

Cinco procesos: licencias, farmacos, auditoria, reintegro, controles.
RBAC: Administrativo y Coordinacion crean/actualizan; Auditor solo lectura.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.models.ventana_proceso import ConfigVentanaProceso
from app.schemas.ventana_proceso import VentanaProcesoCreate, VentanaProcesoRead

router = APIRouter(prefix="/api/v1/ventanas-proceso", tags=["ventanas-proceso"])

_lector = require_role("Coordinacion", "Auditor", "Administrativo")
_escritor = require_role("Coordinacion", "Administrativo")


@router.get("", response_model=list[VentanaProcesoRead])
def listar_ventanas(
    proceso: str | None = Query(None),
    db: Session = Depends(get_db),
    _current_user=Depends(_lector),
) -> list[ConfigVentanaProceso]:
    """CA-1..CA-3: lista de configuraciones de ventanas por proceso."""
    stmt = select(ConfigVentanaProceso)
    if proceso is not None:
        stmt = stmt.where(ConfigVentanaProceso.proceso == proceso)
    return list(db.scalars(stmt.order_by(ConfigVentanaProceso.proceso)))


@router.post("", response_model=VentanaProcesoRead, status_code=status.HTTP_201_CREATED)
def crear_ventana(
    payload: VentanaProcesoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_escritor),
) -> ConfigVentanaProceso:
    """Crear la configuración de una ventana de proceso."""
    ventana = ConfigVentanaProceso(
        proceso=payload.proceso,
        columnas_visibles=payload.columnas_visibles,
        orden_por_defecto=payload.orden_por_defecto,
        creado_por=current_user.username,
    )
    db.add(ventana)
    db.commit()
    db.refresh(ventana)

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="config_ventana_proceso",
        entity_id=str(ventana.id),
    )
    db.commit()

    return ventana
