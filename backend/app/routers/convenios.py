"""Mantenedor de convenios: lectura para los tres roles; alta, edición y actualización desde
SALUTEM para quienes operan (Coordinación y Administrativo)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, require_role
from app.db.session import get_db
from app.integrations.salutem.client import SalutemStubClient, get_salutem_client
from app.integrations.salutem.errors import SalutemError, SalutemUnavailableError
from app.models.convenio import Convenio
from app.schemas.convenio import (
    ActualizacionConvenios,
    ConvenioCreate,
    ConvenioRead,
    ConvenioSugerido,
    ConvenioUpdate,
)
from app.services import convenios as servicio

router = APIRouter(prefix="/api/v1/convenios", tags=["convenios"])

_lector = require_role("Coordinacion", "Administrativo", "Auditor")
_escritor = require_role("Coordinacion", "Administrativo")


@router.get("", response_model=list[ConvenioRead])
def listar(
    solo_seleccionables: bool = False,
    db: Session = Depends(get_db),
    _usuario: CurrentUser = Depends(_lector),
) -> list[Convenio]:
    return servicio.listar_convenios(db, solo_seleccionables=solo_seleccionables)


# Las rutas fijas van antes de ``/{convenio_id}``.
@router.get("/para-reportes", response_model=list[str])
def para_reportes(db: Session = Depends(get_db), _usuario: CurrentUser = Depends(_lector)) -> list[str]:
    return servicio.nombres_para_reportes(db)


@router.get("/sugerido", response_model=ConvenioSugerido)
def sugerido(
    paciente_id: int | None = None,
    rut: str | None = None,
    db: Session = Depends(get_db),
    _usuario: CurrentUser = Depends(_lector),
) -> ConvenioSugerido:
    convenio = servicio.convenio_sugerido(db, paciente_id=paciente_id, rut=rut)
    return ConvenioSugerido(convenio=ConvenioRead.model_validate(convenio) if convenio else None)


@router.post("/actualizar-salutem", response_model=ActualizacionConvenios)
def actualizar_salutem(
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_escritor),
) -> ActualizacionConvenios:
    cliente = get_salutem_client()
    if isinstance(cliente, SalutemStubClient):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SALUTEM no está configurado."
        )
    try:
        resultado = servicio.actualizar_desde_salutem(db, cliente, actor.username)
    except SalutemUnavailableError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="SALUTEM no respondió; intenta más tarde."
        )
    except SalutemError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"SALUTEM rechazó la consulta: {exc}"
        )
    db.commit()
    return ActualizacionConvenios(
        creados=resultado.creados, actualizados=resultado.actualizados,
        desactivados=resultado.desactivados, errores=resultado.errores,
    )


@router.post("", response_model=ConvenioRead, status_code=status.HTTP_201_CREATED)
def crear(
    payload: ConvenioCreate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_escritor),
) -> Convenio:
    convenio = servicio.crear_convenio(db, payload, actor.username, actor.role)
    db.commit()
    db.refresh(convenio)
    return convenio


@router.patch("/{convenio_id}", response_model=ConvenioRead)
def actualizar(
    convenio_id: int,
    payload: ConvenioUpdate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_escritor),
) -> Convenio:
    convenio = servicio.actualizar_convenio(db, convenio_id, payload, actor.username, actor.role)
    db.commit()
    db.refresh(convenio)
    return convenio
