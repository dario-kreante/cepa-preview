"""Seguimiento del proceso clínico y validador de plazos por programa (CEPA-013, D10)."""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.ingreso import Ingreso
from app.models.plazo_programa import PlazoPrograma
from app.models.seguimiento import Seguimiento
from app.schemas.seguimiento import SeguimientoUpdate


def _obtener_ingreso(db, ingreso_id: int) -> Ingreso:
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    return ingreso


def upsert_seguimiento(db, ingreso_id: int, data: SeguimientoUpdate) -> Seguimiento:
    """Crea o actualiza (parcialmente) el seguimiento del ingreso."""
    _obtener_ingreso(db, ingreso_id)
    seg = db.execute(
        select(Seguimiento).where(Seguimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if seg is None:
        seg = Seguimiento(ingreso_id=ingreso_id)
        db.add(seg)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        # los Enum se persisten como su .value
        if hasattr(valor, "value"):
            valor = valor.value
        setattr(seg, campo, valor)
    db.flush()
    return seg


def validar_plazo(db, ingreso_id: int) -> dict:
    """Compara la fecha de la evaluación (la más temprana realizada) contra el plazo
    del programa, medido desde la fecha de ingreso (D10).

    Devuelve cumplimiento: en_plazo / fuera_de_plazo / sin_datos.
    """
    ingreso = _obtener_ingreso(db, ingreso_id)
    seg = db.execute(
        select(Seguimiento).where(Seguimiento.ingreso_id == ingreso_id)
    ).scalar_one_or_none()
    if seg is None or seg.programa is None:
        return {"cumplimiento": "sin_datos", "detalle": "No hay seguimiento o programa definido."}

    plazo = db.get(PlazoPrograma, seg.programa)
    if plazo is None:
        return {"cumplimiento": "sin_datos", "detalle": f"Programa {seg.programa} sin plazo configurado."}

    fechas = [f for f in (seg.eval_medica_fecha, seg.eval_psico_fecha) if f is not None]
    if not fechas:
        return {"cumplimiento": "sin_datos", "detalle": "No hay fecha de evaluación registrada."}

    fecha_eval = max(fechas)  # la última evaluación define el cumplimiento
    limite = ingreso.fecha_ingreso + timedelta(days=plazo.dias_plazo_informe)
    if fecha_eval <= limite:
        return {"cumplimiento": "en_plazo", "detalle": f"Evaluación al {fecha_eval} (límite {limite})."}
    return {"cumplimiento": "fuera_de_plazo", "detalle": f"Evaluación al {fecha_eval} (límite {limite})."}
