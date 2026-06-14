"""Generación de folios secuenciales portables (CEPA-011 RN-1/RN-5).

El correlativo se reserva con un SELECT ... FOR UPDATE sobre `folio_seq`,
evitando secuencias específicas de motor. Formato: F-<anio>-<correlativo 4 díg.>.
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.folio_seq import FolioSeq
from app.models.ingreso import Ingreso


def _anio_actual() -> int:
    return datetime.now(timezone.utc).year


def siguiente_folio(db, anio: int | None = None) -> str:
    """Reserva y devuelve el siguiente folio secuencial para el año dado (UTC).

    Bloquea la fila del contador del año para evitar correlativos duplicados bajo
    concurrencia. El caller hace commit junto con el ingreso.
    """
    anio = anio or _anio_actual()
    fila = db.execute(
        select(FolioSeq).where(FolioSeq.anio == anio).with_for_update()
    ).scalar_one_or_none()
    if fila is None:
        fila = FolioSeq(anio=anio, ultimo=0)
        db.add(fila)
        db.flush()
        fila = db.execute(
            select(FolioSeq).where(FolioSeq.anio == anio).with_for_update()
        ).scalar_one()
    fila.ultimo += 1
    db.flush()
    return f"F-{anio}-{fila.ultimo:04d}"


def folio_existe(db, folio: str) -> bool:
    """True si ya existe un ingreso con ese folio."""
    return db.execute(
        select(Ingreso.id).where(Ingreso.folio == folio)
    ).scalar_one_or_none() is not None
