"""Router IMED — CEPA-122 (P2, diferible).

Se activa con IMED_ENABLED=true (PA5). Cuando está deshabilitado, los endpoints
responden 503 para no bloquear a los clientes existentes. El contrato es parte
de v1 sin rediseño (CA-3 CEPA-122 RN-4).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.config import get_settings
from app.db.session import get_db
from app.schemas.imed import ImedLicenciaCreate, ImedPayloadRead, ImedRecetaCreate
from app.services.imed import recibir_payload_imed

router = APIRouter(prefix="/api/v1/imed", tags=["imed"])

_writer = require_role("Administrativo", "Coordinacion")


def _verificar_imed_habilitado() -> None:
    if not get_settings().imed_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integración IMED pendiente de habilitación (PA5). Contactar a Coordinación CEPA.",
        )


@router.post(
    "/licencias",
    response_model=ImedPayloadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Recepción de licencia médica electrónica desde IMED (CA-1)",
    dependencies=[Depends(_writer)],
)
def recibir_licencia_imed(
    payload: ImedLicenciaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ImedPayloadRead:
    """TC-122-01: IMED envía licencia → CEPA persiste y confirma (RN-1, RN-3, RN-4)."""
    _verificar_imed_habilitado()
    registro = recibir_payload_imed(db, payload.folio, payload.tipo, payload.datos)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="imed_payload",
        entity_id=str(registro.id),
    )
    db.commit()
    db.refresh(registro)
    return registro


@router.post(
    "/recetas",
    response_model=ImedPayloadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Recepción de receta electrónica desde IMED (CA-2)",
    dependencies=[Depends(_writer)],
)
def recibir_receta_imed(
    payload: ImedRecetaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ImedPayloadRead:
    """TC-122-02: IMED envía receta → CEPA persiste y confirma (RN-1, RN-3, RN-4)."""
    _verificar_imed_habilitado()
    registro = recibir_payload_imed(db, payload.folio, payload.tipo, payload.datos)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="imed_payload",
        entity_id=str(registro.id),
    )
    db.commit()
    db.refresh(registro)
    return registro
