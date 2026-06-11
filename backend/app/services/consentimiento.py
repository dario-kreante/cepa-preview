"""Validador de consentimiento informado (CEPA-016, v4 D9)."""

from fastapi import HTTPException, status
from sqlalchemy import select

from app.domain.enums import EstadoConsentimiento
from app.models.consentimiento import Consentimiento
from app.models.ingreso import Ingreso
from app.schemas.consentimiento import ConsentimientoUpdate


def _obtener_ingreso(db, ingreso_id: int) -> Ingreso:
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    return ingreso


def upsert_consentimiento(db, ingreso_id: int, data: ConsentimientoUpdate) -> Consentimiento:
    _obtener_ingreso(db, ingreso_id)
    consent = db.execute(
        select(Consentimiento).where(Consentimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if consent is None:
        consent = Consentimiento(ingreso_id=ingreso_id)
        db.add(consent)
    consent.estado = data.estado.value
    if data.evidencia_ref is not None:
        consent.evidencia_ref = data.evidencia_ref
    if data.fecha_firma is not None:
        consent.fecha_firma = data.fecha_firma
    db.flush()
    return consent


def iniciar_tratamiento(db, ingreso_id: int) -> Ingreso:
    """Bloquea el inicio si el consentimiento no está firmado (D9 RN-1)."""
    ingreso = _obtener_ingreso(db, ingreso_id)
    consent = db.execute(
        select(Consentimiento).where(Consentimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if consent is None or consent.estado != EstadoConsentimiento.FIRMADO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede iniciar el tratamiento: el consentimiento informado es obligatorio y debe estar firmado.",
        )
    ingreso.tratamiento_iniciado = True
    db.flush()
    return ingreso


def consentimientos_pendientes(db) -> list[Consentimiento]:
    return list(
        db.execute(
            select(Consentimiento)
            .where(Consentimiento.estado == EstadoConsentimiento.PENDIENTE.value)
            .order_by(Consentimiento.id)
        ).scalars()
    )
