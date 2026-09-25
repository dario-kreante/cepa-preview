"""COMP-2609-07 — Configuración de alertas (umbrales por tipo) y calendario de festivos.

RBAC: Coordinación, Administrativo y Auditor leen; solo Coordinación escribe.
Toda escritura queda auditada (record_audit antes del único commit).
El job de alertas lee estos valores en cada ejecución: no hace falta reiniciar nada.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import require_role
from app.db.session import get_db
from app.models.config_alerta import ConfigAlerta, Festivo
from app.schemas.config_alertas import (
    ConfigAlertaItem,
    ConfigAlertaRead,
    FestivoCreate,
    FestivoRead,
)
from app.services.config_alertas import cargar_ventanas

router = APIRouter(prefix="/api/v1/config-alertas", tags=["config-alertas"])

_lector = require_role("Coordinacion", "Administrativo", "Auditor")
_escritor = require_role("Coordinacion")


def _leer_config(db: Session) -> list[ConfigAlertaRead]:
    ventanas = cargar_ventanas(db)
    autores = {c.tipo: c.actualizado_por for c in db.scalars(select(ConfigAlerta))}
    return [
        ConfigAlertaRead(tipo=tipo, actualizado_por=autores.get(tipo), **valores)
        for tipo, valores in ventanas.items()
    ]


@router.get("", response_model=list[ConfigAlertaRead])
def listar_config(
    db: Session = Depends(get_db), _usuario=Depends(_lector)
) -> list[ConfigAlertaRead]:
    """Los 7 tipos de alerta con su ventana vigente (o el valor por defecto)."""
    return _leer_config(db)


@router.put("", response_model=list[ConfigAlertaRead])
def actualizar_config(
    payload: list[ConfigAlertaItem],
    db: Session = Depends(get_db),
    current_user=Depends(_escritor),
) -> list[ConfigAlertaRead]:
    """Actualiza (o crea) la configuración de los tipos enviados; el resto no cambia."""
    for item in payload:
        tipo = item.tipo.value
        fila = db.scalars(select(ConfigAlerta).where(ConfigAlerta.tipo == tipo)).one_or_none()
        nuevo = {"dias": item.dias, "habiles": item.habiles, "activo": item.activo}
        anterior = None
        if fila is None:
            fila = ConfigAlerta(tipo=tipo)
            db.add(fila)
        else:
            anterior = {"dias": fila.dias, "habiles": bool(fila.habiles), "activo": bool(fila.activo)}
            if anterior == nuevo:
                continue
        fila.dias, fila.habiles, fila.activo = item.dias, item.habiles, item.activo
        fila.actualizado_por = current_user.username
        db.flush()
        record_audit(
            db,
            actor=current_user.username,
            rol=current_user.role,
            action="UPDATE" if anterior is not None else "CREATE",
            entity="config_alerta",
            entity_id=tipo,
            valor_anterior=json.dumps(anterior) if anterior is not None else None,
            valor_nuevo=json.dumps(nuevo),
        )
    db.commit()
    return _leer_config(db)


@router.get("/festivos", response_model=list[FestivoRead])
def listar_festivos(db: Session = Depends(get_db), _usuario=Depends(_lector)) -> list[Festivo]:
    return list(db.scalars(select(Festivo).order_by(Festivo.fecha)))


@router.post("/festivos", response_model=FestivoRead, status_code=status.HTTP_201_CREATED)
def crear_festivo(
    payload: FestivoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_escritor),
) -> Festivo:
    existente = db.scalars(select(Festivo).where(Festivo.fecha == payload.fecha)).one_or_none()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un festivo el {payload.fecha.isoformat()}",
        )
    festivo = Festivo(fecha=payload.fecha, descripcion=payload.descripcion.strip())
    db.add(festivo)
    db.flush()
    record_audit(
        db,
        actor=current_user.username,
        rol=current_user.role,
        action="CREATE",
        entity="festivo",
        entity_id=str(festivo.id),
        valor_nuevo=json.dumps({"fecha": payload.fecha.isoformat(), "descripcion": festivo.descripcion}),
    )
    db.commit()
    db.refresh(festivo)
    return festivo


@router.delete("/festivos/{festivo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_festivo(
    festivo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(_escritor),
) -> Response:
    festivo = db.get(Festivo, festivo_id)
    if festivo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Festivo no encontrado")
    anterior = json.dumps({"fecha": festivo.fecha.isoformat(), "descripcion": festivo.descripcion})
    db.delete(festivo)
    record_audit(
        db,
        actor=current_user.username,
        rol=current_user.role,
        action="DELETE",
        entity="festivo",
        entity_id=str(festivo_id),
        valor_anterior=anterior,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
