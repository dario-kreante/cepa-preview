"""Catálogo de tramos de GAF en BD — v5 D18, COMP-2609-12."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.domain.gaf import Tramo, tramo_que_contiene
from app.models.gaf_tramo import GafTramo


def listar_tramos(db: Session) -> list[GafTramo]:
    """Tramos activos, en el orden del catálogo."""
    return list(
        db.scalars(select(GafTramo).where(GafTramo.activo == true()).order_by(GafTramo.orden))
    )


def cargar_tramos(db: Session) -> list[Tramo]:
    return [Tramo(t.desde, t.hasta, t.etiqueta) for t in listar_tramos(db)]


def resolver_tramo(db: Session, etiqueta: str | None, entero: int | None) -> str | None:
    """Tramo a guardar: el elegido (validado contra el catálogo) o el que contiene al entero.

    Raises:
        HTTPException 422: si la etiqueta no es un tramo activo del catálogo.
    """
    tramos = cargar_tramos(db)
    if etiqueta is not None:
        if etiqueta not in {t.etiqueta for t in tramos}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El tramo de GAF '{etiqueta}' no está en el catálogo.",
            )
        return etiqueta
    tramo = tramo_que_contiene(entero, tramos)
    return tramo.etiqueta if tramo else None
