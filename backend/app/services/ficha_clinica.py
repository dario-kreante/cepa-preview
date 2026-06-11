"""Servicio de fichas clínicas — push/pull bidireccional (CEPA-121 CA-3).

D12: solo lectura hacia SALUTEM. La persistencia es siempre en el dominio CEPA.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.client import get_salutem_client
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.schemas.ficha_clinica import FichaClinicaCreate


def _obtener_ingreso_por_folio(db: Session, folio: str) -> Ingreso:
    ingreso = db.execute(
        select(Ingreso).where(Ingreso.folio == folio)
    ).scalar_one_or_none()
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un ingreso con folio {folio!r}",
        )
    return ingreso


def crear_ficha(db: Session, data: FichaClinicaCreate) -> FichaClinica:
    """Push: persiste datos clínicos recibidos en el dominio CEPA (D12)."""
    ingreso = _obtener_ingreso_por_folio(db, data.folio)
    ficha = FichaClinica(
        ingreso_id=ingreso.id,
        folio=data.folio,
        origen=data.origen,
        contenido=data.contenido,
    )
    db.add(ficha)
    db.flush()
    return ficha


def listar_fichas(db: Session, folio: str) -> list[FichaClinica]:
    """Pull: devuelve todas las fichas clínicas del dominio CEPA para el folio."""
    _obtener_ingreso_por_folio(db, folio)
    return list(
        db.scalars(select(FichaClinica).where(FichaClinica.folio == folio)).all()
    )


def pull_desde_salutem(db: Session, folio: str) -> FichaClinica | None:
    """Pull desde SALUTEM: obtiene datos clínicos (solo lectura) y los persiste en CEPA.

    D12 garantizado: get_salutem_client() solo expone métodos de lectura.
    Si SALUTEM no tiene datos para el folio, devuelve None.
    """
    _obtener_ingreso_por_folio(db, folio)
    cliente = get_salutem_client()
    # Solo lectura sobre SALUTEM (D12): get_ficha_clinica es un método de lectura
    datos_salutem = cliente.get_ficha_clinica(folio)
    if datos_salutem is None:
        return None
    # Persistir en el dominio CEPA (no en SALUTEM)
    return crear_ficha(
        db,
        FichaClinicaCreate(folio=folio, origen="SALUTEM", contenido=datos_salutem),
    )
