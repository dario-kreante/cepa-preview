"""Cierre y alta del caso (CEPA-014) y cierre con motivo / reapertura (QA-011)."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select

from app.audit.service import record_audit
from app.domain.enums import EstadoCaso, MotivoCierre
from app.models.ingreso import Ingreso
from app.models.ingreso_cierre import HistorialCierre
from app.models.usuario import ROL_SUPERADMIN
from app.schemas.ingreso import IngresoCierre
from app.services.alertas_cierre import resolver_alertas_de_ingreso

# Perfiles que pueden reabrir un caso cerrado.
ROLES_REABRIR = ("Coordinacion", ROL_SUPERADMIN)
_SANTIAGO = ZoneInfo("America/Santiago")


def _obtener(db, ingreso_id: int) -> Ingreso:
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    return ingreso


def _resumen_cierre(ingreso: Ingreso) -> str:
    return (
        f"estado={ingreso.estado}|motivo={ingreso.motivo_cierre}"
        f"|fecha_cierre={ingreso.fecha_cierre.isoformat() if ingreso.fecha_cierre else None}"
        f"|cierre_usuario={ingreso.cierre_usuario}"
    )


def _cerrar(db, ingreso: Ingreso, motivo: MotivoCierre | None, actor: str, rol: str | None) -> None:
    if motivo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe indicar el motivo de cierre."
        )
    anterior = _resumen_cierre(ingreso)
    ingreso.estado = EstadoCaso.CERRADO.value
    ingreso.motivo_cierre = motivo.value
    ingreso.fecha_cierre = datetime.now(timezone.utc)
    ingreso.cierre_usuario = actor
    db.add(
        HistorialCierre(
            ingreso_id=ingreso.id,
            motivo_cierre=motivo.value,
            fecha_cierre=ingreso.fecha_cierre.astimezone(_SANTIAGO).date(),
            cerrado_por=actor,
            cerrado_en=ingreso.fecha_cierre,
        )
    )
    db.flush()
    resolver_alertas_de_ingreso(db, ingreso.id)
    record_audit(
        db, actor=actor, rol=rol, action="UPDATE", entity="ingreso", entity_id=str(ingreso.id),
        valor_anterior=anterior, valor_nuevo=_resumen_cierre(ingreso),
    )


def _reabrir(
    db, ingreso: Ingreso, nuevo: EstadoCaso, actor: str, rol: str | None, motivo_reapertura: str | None
) -> None:
    if rol not in ROLES_REABRIR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo Coordinación puede reabrir un caso cerrado.",
        )
    anterior = _resumen_cierre(ingreso)
    # El cierre vigente pasa al historial (QA-007): se marca como reabierto, no se borra.
    abierto = db.scalars(
        select(HistorialCierre)
        .where(HistorialCierre.ingreso_id == ingreso.id, HistorialCierre.reabierto_en.is_(None))
        .order_by(HistorialCierre.cerrado_en.desc(), HistorialCierre.id.desc())
        .limit(1)
    ).first()
    if abierto is not None:
        abierto.reabierto_por = actor
        abierto.reabierto_en = datetime.now(timezone.utc)
        abierto.motivo_reapertura = (motivo_reapertura or "").strip() or None
    ingreso.estado = nuevo.value
    ingreso.motivo_cierre = None
    ingreso.fecha_cierre = None
    ingreso.cierre_usuario = None
    db.flush()
    record_audit(
        db, actor=actor, rol=rol, action="UPDATE", entity="ingreso", entity_id=str(ingreso.id),
        valor_anterior=anterior, valor_nuevo=_resumen_cierre(ingreso),
    )


def cambiar_estado(
    db,
    ingreso_id: int,
    estado: EstadoCaso,
    *,
    motivo_cierre: MotivoCierre | None,
    actor: str,
    rol: str | None,
    motivo_reapertura: str | None = None,
) -> Ingreso:
    """Cambia el estado del ingreso. Cerrar exige motivo; salir de «cerrado» exige Coordinación."""
    ingreso = _obtener(db, ingreso_id)
    if ingreso.estado == EstadoCaso.CERRADO.value:
        if estado == EstadoCaso.CERRADO:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El caso ya está cerrado.")
        if motivo_cierre is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El motivo de cierre solo aplica al cerrar el caso.",
            )
        _reabrir(db, ingreso, estado, actor, rol, motivo_reapertura)
        return ingreso
    if motivo_reapertura is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El motivo de reapertura solo aplica al reabrir un caso cerrado.",
        )
    if estado == EstadoCaso.CERRADO:
        _cerrar(db, ingreso, motivo_cierre, actor, rol)
        return ingreso
    if motivo_cierre is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El motivo de cierre solo aplica al cerrar el caso.",
        )
    ingreso.estado = estado.value
    db.flush()
    return ingreso


def historial_cierres(db, ingreso_id: int) -> list[HistorialCierre]:
    """Cierres del ingreso, el más reciente primero (QA-007)."""
    _obtener(db, ingreso_id)
    return list(
        db.scalars(
            select(HistorialCierre)
            .where(HistorialCierre.ingreso_id == ingreso_id)
            .order_by(HistorialCierre.cerrado_en.desc(), HistorialCierre.id.desc())
        )
    )


def cerrar_ingreso(db, ingreso_id: int, data: IngresoCierre, *, actor: str, rol: str | None = None) -> Ingreso:
    """Cierre/alta (CEPA-014). Un caso ya cerrado no se toca por esta vía: se reabre por /estado."""
    ingreso = _obtener(db, ingreso_id)
    if ingreso.estado == EstadoCaso.CERRADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El caso ya está cerrado; solo Coordinación puede reabrirlo.",
        )
    if data.estado == EstadoCaso.CERRADO:
        _cerrar(db, ingreso, data.motivo_cierre, actor, rol)
    else:
        ingreso.estado = data.estado.value
    if data.tipo_alta is not None:
        ingreso.tipo_alta = data.tipo_alta.value
    if data.fecha_alta is not None:
        ingreso.fecha_alta = data.fecha_alta
    if data.flag_revision is not None:
        ingreso.flag_revision = data.flag_revision
    if data.observaciones is not None:
        ingreso.observaciones = data.observaciones
    db.flush()
    return ingreso
