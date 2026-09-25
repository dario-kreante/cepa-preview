"""COMP-2609-12 — Catálogo de tramos de GAF (v5 D18). Lectura para los tres roles."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.services.gaf_tramos import listar_tramos

router = APIRouter(prefix="/api/v1/gaf-tramos", tags=["gaf-tramos"])

_lector = require_role("Coordinacion", "Administrativo", "Auditor")


class GafTramoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    desde: int
    hasta: int
    etiqueta: str
    orden: int
    # True mientras la segmentación no esté confirmada por la contraparte (PA-v5-03).
    provisorio: bool


@router.get("", response_model=list[GafTramoRead])
def listar(db: Session = Depends(get_db), _usuario=Depends(_lector)) -> list:
    """Tramos de GAF activos, en orden."""
    return listar_tramos(db)
