"""Operaciones CRUD sobre LicenciaMedica — CEPA-070 / CEPA-073."""

import datetime

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.schemas.licencia import LicenciaAnularUpdate, LicenciaCreate, LicenciaISLUpdate
from app.domain.enums_licencia import EstadoEnvioISL


def _verificar_ingreso(db, ingreso_id: int) -> Ingreso:
    ing = db.execute(select(Ingreso).where(Ingreso.id == ingreso_id)).scalar_one_or_none()
    if ing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe ingreso con id={ingreso_id}.",
        )
    return ing


def _calcular_advertencia_dias(data: LicenciaCreate) -> str | None:
    """RN-5 CEPA-070: advierte si cantidad_dias no coincide con (termino - inicio + 1)."""
    dias_calculados = (data.fecha_termino - data.fecha_inicio).days + 1
    if dias_calculados != data.cantidad_dias:
        return (
            f"cantidad_dias={data.cantidad_dias} no coincide con "
            f"(fecha_termino - fecha_inicio + 1)={dias_calculados}. "
            "Verifique si es prórroga/empalme antes de confirmar."
        )
    return None


def crear_licencia(db, data: LicenciaCreate) -> tuple[LicenciaMedica, str | None]:
    """Crea una LM. Devuelve (objeto, advertencia_dias|None)."""
    _verificar_ingreso(db, data.ingreso_id)
    advertencia = _calcular_advertencia_dias(data)
    lm = LicenciaMedica(
        ingreso_id=data.ingreso_id,
        folio_lm=data.folio_lm,
        tipo_lm=data.tipo_lm.value,
        tipo_reposo=data.tipo_reposo.value,
        fecha_inicio=data.fecha_inicio,
        fecha_termino=data.fecha_termino,
        fecha_emision=data.fecha_emision,
        inicio_reposo=data.inicio_reposo,
        fin_reposo=data.fin_reposo,
        cantidad_dias=data.cantidad_dias,
        indicacion_reposo=data.indicacion_reposo,
        diagnostico=data.diagnostico,
        origen=data.origen.value,
        envio_isl="pendiente",
        anulada=False,
    )
    db.add(lm)
    db.flush()
    return lm, advertencia


def obtener_licencia(db, licencia_id: int) -> LicenciaMedica:
    lm = db.execute(
        select(LicenciaMedica).where(LicenciaMedica.id == licencia_id)
    ).scalar_one_or_none()
    if lm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe licencia con id={licencia_id}.",
        )
    return lm


def listar_licencias_por_ingreso(db, ingreso_id: int) -> list[LicenciaMedica]:
    _verificar_ingreso(db, ingreso_id)
    return list(
        db.scalars(
            select(LicenciaMedica)
            .where(LicenciaMedica.ingreso_id == ingreso_id)
            .order_by(LicenciaMedica.fecha_inicio)
        )
    )


def anular_licencia(db, licencia_id: int, data: LicenciaAnularUpdate) -> LicenciaMedica:
    lm = obtener_licencia(db, licencia_id)
    if lm.anulada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La licencia ya está anulada.",
        )
    lm.anulada = True
    lm.observaciones = (lm.observaciones or "") + f" [ANULADA: {data.observaciones}]"
    db.flush()
    return lm


def actualizar_isl(db, licencia_id: int, data: LicenciaISLUpdate) -> LicenciaMedica:
    """Actualiza la trazabilidad ISL de una LM (CEPA-073 RN-1/RN-2)."""
    lm = obtener_licencia(db, licencia_id)
    lm.envio_isl = data.envio_isl.value
    lm.fecha_envio_isl = data.fecha_envio_isl
    if data.eeag_gaf is not None:
        lm.eeag_gaf = data.eeag_gaf
    if data.observaciones is not None:
        lm.observaciones = data.observaciones
    db.flush()
    return lm
