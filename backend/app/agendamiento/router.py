"""Router de agendamiento — EPIC-08.

Endpoints:
  POST   /api/v1/disponibilidad-profesional          Administrativo | Coordinacion
  GET    /api/v1/disponibilidad-profesional/{prof_id} Todos los roles
  POST   /api/v1/propuestas-agenda                   Administrativo | Coordinacion
  GET    /api/v1/propuestas-agenda                   Todos los roles
  GET    /api/v1/propuestas-agenda/{id}              Todos los roles
  POST   /api/v1/propuestas-agenda/{id}/confirmar    Administrativo | Coordinacion
  GET    /api/v1/propuestas-agenda/{id}/citas        Todos los roles
  POST   /api/v1/pacientes-por-citar/{paciente_id}/gestiones  Administrativo | Coordinacion
  GET    /api/v1/pacientes-por-citar/{paciente_id}/gestiones  Todos los roles
  GET    /api/v1/pacientes-por-citar                 Todos los roles
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.agendamiento import gestion, lista
from app.agendamiento.models import (
    CitaPropuesta,
    DisponibilidadProf,
    GestionCitacion,
    PropuestaAgenda,
)
from app.agendamiento.schemas import (
    CitaPropuestaRead,
    ConfirmarCitasRequest,
    DisponibilidadProfCreate,
    DisponibilidadProfRead,
    GenerarPropuestaRequest,
    GestionCreate,
    GestionRead,
    PacientesPorCitarRead,
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
from app.models.profesional import Profesional
from app.services.salutem_sync.incremental import hoy_en_santiago

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
    dp = crear_disponibilidad(
        db=db,
        profesional_id=payload.profesional_id,
        dia_semana=payload.dia_semana.value,
        cupo_diario=payload.cupo_diario,
        actor=current_user.username,
    )
    db.commit()  # persistir: el servicio solo hace flush (bug CEPA-080)
    db.refresh(dp)
    return dp


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
               DisponibilidadProf.activo == true())
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


# ─── Gestión de contacto ───────────────────────────────────────────────────────

@router.post(
    "/api/v1/pacientes-por-citar/{paciente_id}/gestiones",
    response_model=GestionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_writer],
)
def registrar_gestion_endpoint(
    paciente_id: int,
    payload: GestionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> GestionCitacion:
    g = gestion.registrar_gestion(
        db,
        paciente_id=paciente_id,
        profesional_id=payload.profesional_id,
        resultado=payload.resultado,
        nota=payload.nota,
        actor=current_user.username,
        rol=current_user.role,
    )
    db.commit()
    db.refresh(g)
    return g


@router.get(
    "/api/v1/pacientes-por-citar/{paciente_id}/gestiones",
    response_model=list[GestionRead],
    dependencies=[_reader],
)
def listar_gestiones_endpoint(
    paciente_id: int, db: Session = Depends(get_db)
) -> list[GestionCitacion]:
    return gestion.listar_gestiones(db, paciente_id)


# ─── Lista calculada de pacientes por citar ────────────────────────────────────

_MAX_DIAS_RANGO = 62


def _hoy() -> date:
    return hoy_en_santiago(datetime.now(timezone.utc))


@router.get(
    "/api/v1/pacientes-por-citar",
    response_model=PacientesPorCitarRead,
    dependencies=[_reader],
)
def pacientes_por_citar_endpoint(
    profesional_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
) -> PacientesPorCitarRead:
    prof = db.get(Profesional, profesional_id)
    if prof is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesional no encontrado")
    if not prof.activo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El profesional está inactivo"
        )
    hoy = _hoy()
    desde = desde or hoy
    if hasta is None:
        # viernes de la semana siguiente a la de `desde`
        hasta = desde - timedelta(days=desde.weekday()) + timedelta(days=7 + 4)
    if hasta < desde:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="'hasta' no puede ser anterior a 'desde'"
        )
    if (hasta - desde).days > _MAX_DIAS_RANGO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El rango no puede superar {_MAX_DIAS_RANGO} días",
        )
    return lista.calcular_pacientes_por_citar(db, profesional_id, desde, hasta, hoy)
