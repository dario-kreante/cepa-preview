"""Catálogo de profesionales para el agendamiento.

Lectura para los tres roles (la Agenda lo usa como selector); alta, edición e importación
desde SALUTEM para quienes operan la agenda (Coordinación y Administrativo).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, require_role
from app.db.session import get_db
from app.models.profesional import Profesional
from app.schemas.profesional import (
    ImportacionSalutemResultado,
    ProfesionalCreate,
    ProfesionalRead,
    ProfesionalUpdate,
)
from app.services import profesionales as servicio

router = APIRouter(prefix="/api/v1/profesionales", tags=["profesionales"])

_lector = require_role("Coordinacion", "Administrativo", "Auditor")
_escritor = require_role("Coordinacion", "Administrativo")


@router.get("", response_model=list[ProfesionalRead])
def listar(
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    _usuario: CurrentUser = Depends(_lector),
) -> list[Profesional]:
    return servicio.listar_profesionales(db, solo_activos=solo_activos)


@router.post("", response_model=ProfesionalRead, status_code=status.HTTP_201_CREATED)
def crear(
    payload: ProfesionalCreate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_escritor),
) -> Profesional:
    profesional = servicio.crear_profesional(db, payload, actor.username, actor.role)
    db.commit()
    db.refresh(profesional)
    return profesional


@router.patch("/{profesional_id}", response_model=ProfesionalRead)
def actualizar(
    profesional_id: int,
    payload: ProfesionalUpdate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_escritor),
) -> Profesional:
    profesional = servicio.actualizar_profesional(
        db, profesional_id, payload, actor.username, actor.role
    )
    db.commit()
    db.refresh(profesional)
    return profesional


@router.post("/importar-salutem", response_model=ImportacionSalutemResultado)
def importar_salutem(
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(_escritor),
) -> ImportacionSalutemResultado:
    creados = servicio.importar_desde_salutem(db, actor.username, actor.role)
    db.commit()
    return ImportacionSalutemResultado(creados=creados)
