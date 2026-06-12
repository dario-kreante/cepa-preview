"""Servicio de recepción IMED (CEPA-122).

Persiste el payload entrante en imed_payload y registra auditoría.
Si el folio no existe en el CEPA → 404 (el CEPA no crea registros fantasma).
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.imed_payload import ImedPayload
from app.models.ingreso import Ingreso


def _verificar_folio(db: Session, folio: str) -> None:
    existe = db.execute(
        select(Ingreso.id).where(Ingreso.folio == folio)
    ).scalar_one_or_none()
    if existe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un ingreso con folio {folio!r} en el CEPA",
        )


def recibir_payload_imed(db: Session, folio: str, tipo: str, datos: dict) -> ImedPayload:
    """Persiste el payload IMED en el inbox del dominio CEPA."""
    _verificar_folio(db, folio)
    payload = ImedPayload(folio=folio, tipo=tipo, datos=datos)
    db.add(payload)
    db.flush()
    return payload
