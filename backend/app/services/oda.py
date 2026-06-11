"""Registro de ODAS y alerta de vencimiento (CEPA-015, v4 D3)."""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update

from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.schemas.oda import OdaCreate

VENTANA_ALERTA_DIAS = 5  # ventana por defecto de "ODA por vencer"


def registrar_oda(db, ingreso_id: int, data: OdaCreate) -> Oda:
    """Registra una ODA. La nueva queda vigente; las previas del ingreso pasan a no vigentes
    (se conserva el historial, RN-5)."""
    if db.get(Ingreso, ingreso_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    db.execute(update(Oda).where(Oda.ingreso_id == ingreso_id).values(vigente=False))
    oda = Oda(
        ingreso_id=ingreso_id,
        identificador=data.identificador,
        fecha_vencimiento=data.fecha_vencimiento,
        vigente=True,
    )
    db.add(oda)
    db.flush()
    return oda


def listar_odas(db, ingreso_id: int) -> list[Oda]:
    return list(
        db.execute(
            select(Oda).where(Oda.ingreso_id == ingreso_id).order_by(Oda.id)
        ).scalars()
    )


def odas_por_vencer(db, ventana_dias: int = VENTANA_ALERTA_DIAS) -> list[Oda]:
    """ODAS vigentes que vencen entre hoy y hoy+ventana (inclusive ambos extremos)."""
    hoy = date.today()
    limite = hoy + timedelta(days=ventana_dias)
    return list(
        db.execute(
            select(Oda)
            .where(Oda.vigente.is_(True))
            .where(Oda.fecha_vencimiento >= hoy)
            .where(Oda.fecha_vencimiento <= limite)
            .order_by(Oda.fecha_vencimiento)
        ).scalars()
    )
