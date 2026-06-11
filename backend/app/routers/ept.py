"""Router EPIC-03: casos EPT, contactos, proceso y plazos.

Prefijo: /api/v1/casos-ept
RBAC:
  - escritura: solo Administrativo (D1).
  - lectura: Administrativo, Coordinacion, Auditor.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ept import PlazoEpt, ProcesoEpt
from app.schemas.ept import (
    CasoEptCreate,
    CasoEptRead,
    CasoEptUpdate,
    ContactoEptCreate,
    ContactoEptPayload,
    ContactoEptRead,
    PlazoEptCreate,
    PlazoEptRead,
    PlazoEptUpdate,
    ProcesoEptCreate,
    ProcesoEptRead,
    ProcesoEptUpdate,
)
from app.services.ept import (
    actualizar_caso_ept,
    actualizar_plazo_ept,
    actualizar_proceso_ept,
    agregar_contacto_ept,
    crear_caso_ept,
    crear_plazo_ept,
    crear_proceso_ept,
    obtener_caso_ept_o_404,
)

router = APIRouter(prefix="/api/v1/casos-ept", tags=["casos-ept"])

_writer = require_role("Administrativo")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ──────────────────────────────
# CasoEpt
# ──────────────────────────────

@router.post(
    "",
    response_model=CasoEptRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: CasoEptCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoEptRead:
    caso = crear_caso_ept(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="caso_ept",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


@router.get(
    "/{caso_id}",
    response_model=CasoEptRead,
    dependencies=[Depends(_reader)],
)
def obtener(caso_id: int, db: Session = Depends(get_db)) -> CasoEptRead:
    return obtener_caso_ept_o_404(db, caso_id)


@router.patch(
    "/{caso_id}",
    response_model=CasoEptRead,
    dependencies=[Depends(_writer)],
)
def actualizar(
    caso_id: int,
    payload: CasoEptUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoEptRead:
    caso = obtener_caso_ept_o_404(db, caso_id)
    caso = actualizar_caso_ept(db, caso, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_ept",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


# ──────────────────────────────
# Contactos EPT
# ──────────────────────────────

@router.post(
    "/{caso_id}/contactos",
    response_model=ContactoEptRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def agregar_contacto(
    caso_id: int,
    payload: ContactoEptPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ContactoEptRead:
    obtener_caso_ept_o_404(db, caso_id)
    # forzar caso_ept_id desde la URL (no del payload)
    data = ContactoEptCreate(caso_ept_id=caso_id, correo=payload.correo)
    contacto = agregar_contacto_ept(db, data)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="contacto_ept",
        entity_id=str(contacto.id),
    )
    db.commit()
    db.refresh(contacto)
    return contacto


# ──────────────────────────────
# Proceso EPT
# ──────────────────────────────

@router.post(
    "/{caso_id}/proceso",
    response_model=ProcesoEptRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_proceso(
    caso_id: int,
    payload: ProcesoEptCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProcesoEptRead:
    caso = obtener_caso_ept_o_404(db, caso_id)
    proceso = crear_proceso_ept(db, payload, caso)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="proceso_ept",
        entity_id=str(proceso.id),
    )
    db.commit()
    db.refresh(proceso)
    return proceso


@router.get(
    "/{caso_id}/proceso",
    response_model=ProcesoEptRead,
    dependencies=[Depends(_reader)],
)
def obtener_proceso(caso_id: int, db: Session = Depends(get_db)) -> ProcesoEptRead:
    proceso = db.execute(
        select(ProcesoEpt).where(ProcesoEpt.caso_ept_id == caso_id)
    ).scalar_one_or_none()
    if proceso is None:
        raise HTTPException(status_code=404, detail="Proceso EPT no encontrado.")
    return proceso


@router.patch(
    "/{caso_id}/proceso",
    response_model=ProcesoEptRead,
    dependencies=[Depends(_writer)],
)
def actualizar_proceso(
    caso_id: int,
    payload: ProcesoEptUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProcesoEptRead:
    caso = obtener_caso_ept_o_404(db, caso_id)
    proceso = db.execute(
        select(ProcesoEpt).where(ProcesoEpt.caso_ept_id == caso_id)
    ).scalar_one_or_none()
    if proceso is None:
        raise HTTPException(status_code=404, detail="Proceso EPT no encontrado.")
    proceso = actualizar_proceso_ept(db, proceso, payload, caso)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="proceso_ept",
        entity_id=str(proceso.id),
    )
    db.commit()
    db.refresh(proceso)
    return proceso


# ──────────────────────────────
# Plazos EPT
# ──────────────────────────────

@router.post(
    "/{caso_id}/plazos",
    response_model=PlazoEptRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_plazos(
    caso_id: int,
    payload: PlazoEptCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PlazoEptRead:
    caso = obtener_caso_ept_o_404(db, caso_id)
    plazo = crear_plazo_ept(db, payload, caso)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="plazo_ept",
        entity_id=str(plazo.id),
    )
    db.commit()
    db.refresh(plazo)
    return plazo


@router.get(
    "/{caso_id}/plazos",
    response_model=PlazoEptRead,
    dependencies=[Depends(_reader)],
)
def obtener_plazos(caso_id: int, db: Session = Depends(get_db)) -> PlazoEptRead:
    plazo = db.execute(
        select(PlazoEpt).where(PlazoEpt.caso_ept_id == caso_id)
    ).scalar_one_or_none()
    if plazo is None:
        raise HTTPException(status_code=404, detail="Plazos EPT no encontrados.")
    return plazo


@router.patch(
    "/{caso_id}/plazos",
    response_model=PlazoEptRead,
    dependencies=[Depends(_writer)],
)
def actualizar_plazos(
    caso_id: int,
    payload: PlazoEptUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PlazoEptRead:
    caso = obtener_caso_ept_o_404(db, caso_id)
    plazo = db.execute(
        select(PlazoEpt).where(PlazoEpt.caso_ept_id == caso_id)
    ).scalar_one_or_none()
    if plazo is None:
        raise HTTPException(status_code=404, detail="Plazos EPT no encontrados.")
    plazo = actualizar_plazo_ept(db, plazo, payload, caso)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="plazo_ept",
        entity_id=str(plazo.id),
    )
    db.commit()
    db.refresh(plazo)
    return plazo
