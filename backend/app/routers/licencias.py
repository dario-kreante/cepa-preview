"""Router de Licencias Médicas — EPIC-07."""

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.licencia import (
    AcumuladoRead,
    AlertaLicenciaRead,
    LicenciaAnularUpdate,
    LicenciaCreate,
    LicenciaISLUpdate,
    LicenciaRead,
)
from app.services.licencias_acumulado import calcular_acumulado
from app.services.licencias_alerta import generar_alertas_vencimiento
from app.services.licencias_crud import (
    actualizar_isl,
    anular_licencia,
    crear_licencia,
    listar_licencias_por_ingreso,
    obtener_licencia,
)

router = APIRouter(tags=["licencias"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── Acumulado (CEPA-071) — registrado ANTES de /{licencia_id} para evitar
#    que FastAPI interprete "acumulado" como path param ────────────────────────

@router.get(
    "/api/v1/ingresos/{ingreso_id}/licencias/acumulado",
    response_model=AcumuladoRead,
    dependencies=[Depends(_reader)],
)
def acumulado(ingreso_id: int, db: Session = Depends(get_db)) -> AcumuladoRead:
    resultado = calcular_acumulado(db, ingreso_id)
    return AcumuladoRead(
        ingreso_id=resultado.ingreso_id,
        dias_acumulados_vigentes=resultado.dias_acumulados_vigentes,
        dias_acumulados_bruto=resultado.dias_acumulados_bruto,
        hay_solapamiento=resultado.hay_solapamiento,
        incluye_extra_sistema=resultado.incluye_extra_sistema,
    )


# ── Alertas (CEPA-072) ───────────────────────────────────────────────────────

@router.post(
    "/api/v1/licencias/alertas/generar",
    response_model=list[AlertaLicenciaRead],
    dependencies=[Depends(_writer)],
)
def disparar_alertas(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AlertaLicenciaRead]:
    """Endpoint de disparo manual del job de alertas (idempotente).
    El job automático diario lo invocará desde EPIC-10.
    """
    nuevas = generar_alertas_vencimiento(db)
    record_audit(
        db, actor=current_user.username, action="CREATE",
        entity="alerta_licencia", entity_id=f"batch:{len(nuevas)}",
    )
    db.commit()
    return nuevas


# ── Registro y consulta ─────────────────────────────────────────────────────

@router.post(
    "/api/v1/licencias",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: LicenciaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    lm, advertencia = crear_licencia(db, payload)
    record_audit(
        db, actor=current_user.username, action="CREATE",
        entity="licencia_medica", entity_id=str(lm.id),
    )
    db.commit()
    db.refresh(lm)
    respuesta = LicenciaRead.model_validate(lm).model_dump()
    if advertencia:
        respuesta["advertencia_dias"] = advertencia
    return respuesta


@router.get(
    "/api/v1/licencias/{licencia_id}",
    response_model=LicenciaRead,
    dependencies=[Depends(_reader)],
)
def obtener(licencia_id: int, db: Session = Depends(get_db)) -> LicenciaRead:
    return obtener_licencia(db, licencia_id)


@router.get(
    "/api/v1/ingresos/{ingreso_id}/licencias",
    response_model=list[LicenciaRead],
    dependencies=[Depends(_reader)],
)
def historial_por_ingreso(ingreso_id: int, db: Session = Depends(get_db)) -> list[LicenciaRead]:
    return listar_licencias_por_ingreso(db, ingreso_id)


@router.patch(
    "/api/v1/licencias/{licencia_id}/anular",
    response_model=LicenciaRead,
    dependencies=[Depends(_writer)],
)
def anular(
    licencia_id: int,
    payload: LicenciaAnularUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> LicenciaRead:
    lm = anular_licencia(db, licencia_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE",
        entity="licencia_medica", entity_id=str(lm.id),
    )
    db.commit()
    db.refresh(lm)
    return lm


@router.patch(
    "/api/v1/licencias/{licencia_id}/isl",
    response_model=LicenciaRead,
    dependencies=[Depends(_writer)],
)
def actualizar_isl_endpoint(
    licencia_id: int,
    payload: LicenciaISLUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> LicenciaRead:
    lm = actualizar_isl(db, licencia_id, payload)
    record_audit(
        db, actor=current_user.username, action="UPDATE",
        entity="licencia_medica", entity_id=str(lm.id),
    )
    db.commit()
    db.refresh(lm)
    return lm
