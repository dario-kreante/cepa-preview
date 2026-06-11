from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.consentimiento import ConsentimientoRead, ConsentimientoUpdate
from app.schemas.ingreso import IngresoCierre, IngresoCreate, IngresoRead
from app.schemas.seguimiento import SeguimientoRead, SeguimientoUpdate, ValidacionPlazo
from app.services.cierre import cerrar_ingreso
from app.services.consentimiento import iniciar_tratamiento, upsert_consentimiento
from app.services.ingreso import crear_ingreso
from app.services.seguimiento import upsert_seguimiento, validar_plazo

router = APIRouter(prefix="/api/v1/ingresos", tags=["ingresos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.post(
    "",
    response_model=IngresoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: IngresoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngresoRead:
    ingreso = crear_ingreso(db, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE", entity="ingreso", entity_id=str(ingreso.id)
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso


@router.put(
    "/{ingreso_id}/seguimiento",
    response_model=SeguimientoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_seguimiento(
    ingreso_id: int,
    payload: SeguimientoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SeguimientoRead:
    seg = upsert_seguimiento(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="seguimiento", entity_id=str(seg.id)
    )
    db.commit()
    db.refresh(seg)
    return seg


@router.get(
    "/{ingreso_id}/seguimiento/validacion-plazo",
    response_model=ValidacionPlazo,
    dependencies=[Depends(_reader)],
)
def validacion_plazo(ingreso_id: int, db: Session = Depends(get_db)) -> ValidacionPlazo:
    return validar_plazo(db, ingreso_id)


@router.post(
    "/{ingreso_id}/cierre",
    response_model=IngresoRead,
    dependencies=[Depends(_writer)],
)
def cerrar(
    ingreso_id: int,
    payload: IngresoCierre,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngresoRead:
    ingreso = cerrar_ingreso(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="ingreso", entity_id=str(ingreso.id)
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso


@router.put(
    "/{ingreso_id}/consentimiento",
    response_model=ConsentimientoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_consentimiento(
    ingreso_id: int,
    payload: ConsentimientoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ConsentimientoRead:
    consent = upsert_consentimiento(db, ingreso_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="consentimiento", entity_id=str(consent.id)
    )
    db.commit()
    db.refresh(consent)
    return consent


@router.post(
    "/{ingreso_id}/iniciar-tratamiento",
    response_model=IngresoRead,
    dependencies=[Depends(_writer)],
)
def iniciar_tratamiento_endpoint(
    ingreso_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IngresoRead:
    ingreso = iniciar_tratamiento(db, ingreso_id)
    record_audit(
        db, actor=current_user.username, action="UPDATE", entity="ingreso", entity_id=str(ingreso.id)
    )
    db.commit()
    db.refresh(ingreso)
    return ingreso
