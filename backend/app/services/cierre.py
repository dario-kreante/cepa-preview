"""Cierre y alta del caso (CEPA-014)."""

from fastapi import HTTPException, status

from app.models.ingreso import Ingreso
from app.schemas.ingreso import IngresoCierre


def cerrar_ingreso(db, ingreso_id: int, data: IngresoCierre) -> Ingreso:
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")

    ingreso.estado = data.estado.value
    if data.tipo_alta is not None:
        ingreso.tipo_alta = data.tipo_alta.value
    if data.fecha_alta is not None:
        ingreso.fecha_alta = data.fecha_alta
    if data.flag_revision is not None:
        ingreso.flag_revision = data.flag_revision
    if data.observaciones is not None:
        ingreso.observaciones = data.observaciones
    db.flush()
    return ingreso
