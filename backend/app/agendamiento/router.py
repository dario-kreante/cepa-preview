"""Router de agendamiento — EPIC-08.

Endpoints:
  POST   /api/v1/disponibilidad-profesional          Administrativo | Coordinacion
  GET    /api/v1/disponibilidad-profesional/{prof_id} Todos los roles
  POST   /api/v1/propuestas-agenda                   Administrativo | Coordinacion
  GET    /api/v1/propuestas-agenda                   Todos los roles
  GET    /api/v1/propuestas-agenda/{id}              Todos los roles
  POST   /api/v1/propuestas-agenda/{id}/confirmar    Administrativo | Coordinacion
  GET    /api/v1/propuestas-agenda/{id}/citas        Todos los roles
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda
from app.agendamiento.schemas import (
    CitaPropuestaRead,
    ConfirmarCitasRequest,
    DisponibilidadProfCreate,
    DisponibilidadProfRead,
    GenerarPropuestaRequest,
    PropuestaAgendaRead,
)
from app.agendamiento.service import (
    confirmar_citas,
    crear_disponibilidad,
    generar_propuesta,
    obtener_propuesta,
)
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db

router = APIRouter(tags=["agendamiento"])

_writer = Depends(require_role("Administrativo", "Coordinacion"))
_reader = Depends(require_role("Administrativo", "Coordinacion", "Auditor"))


# ─── Disponibilidad ────────────────────────────────────────────────────────────

@router.post(
    "/api/v1/disponibilidad-profesional",
    response_model=DisponibilidadProfRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_writer],
)
def crear_disponibilidad_endpoint(
    payload: DisponibilidadProfCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DisponibilidadProf:
    return crear_disponibilidad(
        db=db,
        profesional_id=payload.profesional_id,
        dia_semana=payload.dia_semana.value,
        cupo_diario=payload.cupo_diario,
        actor=current_user.username,
    )


@router.get(
    "/api/v1/disponibilidad-profesional/{profesional_id}",
    response_model=list[DisponibilidadProfRead],
    dependencies=[_reader],
)
def listar_disponibilidad(
    profesional_id: int,
    db: Session = Depends(get_db),
) -> list[DisponibilidadProf]:
    return list(db.scalars(
        select(DisponibilidadProf)
        .where(DisponibilidadProf.profesional_id == profesional_id,
               DisponibilidadProf.activo.is_(True))
        .order_by(DisponibilidadProf.dia_semana)
    ))


# ─── Propuestas ────────────────────────────────────────────────────────────────

@router.post(
    "/api/v1/propuestas-agenda",
    response_model=PropuestaAgendaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_writer],
)
def crear_propuesta(
    payload: GenerarPropuestaRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PropuestaAgenda:
    propuesta = generar_propuesta(db=db, req=payload, actor=current_user.username)
    db.commit()
    db.refresh(propuesta)
    return propuesta


@router.get(
    "/api/v1/propuestas-agenda",
    response_model=list[PropuestaAgendaRead],
    dependencies=[_reader],
)
def listar_propuestas(
    profesional_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[PropuestaAgenda]:
    q = select(PropuestaAgenda).order_by(PropuestaAgenda.created_at.desc())
    if profesional_id is not None:
        q = q.where(PropuestaAgenda.profesional_id == profesional_id)
    return list(db.scalars(q))


@router.get(
    "/api/v1/propuestas-agenda/{propuesta_id}",
    response_model=PropuestaAgendaRead,
    dependencies=[_reader],
)
def obtener_propuesta_endpoint(
    propuesta_id: int,
    db: Session = Depends(get_db),
) -> PropuestaAgenda:
    propuesta = obtener_propuesta(db=db, propuesta_id=propuesta_id)
    if propuesta is None:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    return propuesta


@router.get(
    "/api/v1/propuestas-agenda/{propuesta_id}/citas",
    response_model=list[CitaPropuestaRead],
    dependencies=[_reader],
)
def listar_citas_de_propuesta(
    propuesta_id: int,
    db: Session = Depends(get_db),
) -> list[CitaPropuesta]:
    return list(db.scalars(
        select(CitaPropuesta)
        .where(CitaPropuesta.propuesta_id == propuesta_id)
        .order_by(CitaPropuesta.fecha_candidata, CitaPropuesta.prioridad)
    ))


@router.post(
    "/api/v1/propuestas-agenda/{propuesta_id}/confirmar",
    response_model=list[CitaPropuestaRead],
    dependencies=[_writer],
)
def confirmar_citas_endpoint(
    propuesta_id: int,
    payload: ConfirmarCitasRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[CitaPropuesta]:
    propuesta = obtener_propuesta(db=db, propuesta_id=propuesta_id)
    if propuesta is None:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    confirmadas = confirmar_citas(
        db=db,
        propuesta_id=propuesta_id,
        cita_ids=payload.cita_ids,
        actor=current_user.username,
    )
    db.commit()
    return confirmadas
