"""Router de Controles Médicos — EPIC-06.

Endpoints:
    POST   /api/v1/controles-medicos                            → crear control (CEPA-060)
    GET    /api/v1/controles-medicos/por-ingreso/{ingreso_id}   → listar por folio
    GET    /api/v1/controles-medicos/{control_id}               → detalle
    PATCH  /api/v1/controles-medicos/{control_id}/proximo-control  → CEPA-061
    PATCH  /api/v1/controles-medicos/{control_id}/licencia         → CEPA-062
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.control_medico import (
    ControlMedicoCreate,
    ControlMedicoRead,
    LicenciaUpdate,
    ProximoControlUpdate,
)
from app.services.control_medico import (
    _get_control_o_404,
    actualizar_licencia,
    crear_control,
    obtener_controles_por_ingreso,
    programar_proximo_control,
)

router = APIRouter(prefix="/api/v1/controles-medicos", tags=["controles-medicos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── CEPA-060: Crear control ───────────────────────────────────────────────────

@router.post(
    "",
    response_model=ControlMedicoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: ControlMedicoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = crear_control(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="control_medico",
        entity_id=str(control.id),
    )
    db.commit()
    db.refresh(control)
    return control


# ── Lectura ───────────────────────────────────────────────────────────────────

@router.get(
    "/por-ingreso/{ingreso_id}",
    response_model=list[ControlMedicoRead],
    dependencies=[Depends(_reader)],
)
def listar_por_ingreso(
    ingreso_id: int,
    db: Session = Depends(get_db),
) -> list[ControlMedicoRead]:
    return obtener_controles_por_ingreso(db, ingreso_id)


@router.get(
    "/{control_id}",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_reader)],
)
def detalle(
    control_id: int,
    db: Session = Depends(get_db),
) -> ControlMedicoRead:
    return _get_control_o_404(db, control_id)


# ── CEPA-061: Próximo control ─────────────────────────────────────────────────

@router.patch(
    "/{control_id}/proximo-control",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_writer)],
)
def programar_proximo(
    control_id: int,
    payload: ProximoControlUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = programar_proximo_control(db, control_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="control_medico",
        entity_id=str(control_id),
    )
    db.commit()
    db.refresh(control)
    return control


# ── CEPA-062: Licencia y RECA ─────────────────────────────────────────────────

@router.patch(
    "/{control_id}/licencia",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_licencia_endpoint(
    control_id: int,
    payload: LicenciaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = actualizar_licencia(db, control_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="control_medico",
        entity_id=str(control_id),
    )
    db.commit()
    db.refresh(control)
    return control
