"""Lógica de negocio del módulo de Seguimiento de Reintegro (EPIC-04).

Las funciones validar_* lanzan HTTPException 422 cuando se viola una regla
de negocio, de modo que el router las puede llamar directamente y FastAPI
convertirá la excepción en una respuesta 422 JSON sin código adicional.
"""

import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.reintegro_enums import EstadoReintegro
from app.models.reintegro import CasoReintegro, Reca
from app.schemas.reintegro import (
    CasoReintegroCreate,
    CasoReintegroUpdate,
    CierreReintegroUpdate,
    RecaCreate,
    RecaUpdate,
)


# ── Validaciones puras (sin sesión) ───────────────────────────────────────

def validar_coherencia_reca(
    solicita_medidas: bool,
    detalle_medidas: str | None,
    fecha_medidas: datetime.date | None,
    verifica_medidas: bool = False,
    fecha_verificacion: datetime.date | None = None,
) -> None:
    """RN-2 y RN-4 CEPA-041.

    - RN-2: si solicita_medidas=True, detalle y fecha son obligatorios.
    - RN-4: si verifica_medidas=True, fecha_verificacion es obligatoria.
    """
    if solicita_medidas:
        if not detalle_medidas:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="detalle_medidas es obligatorio cuando solicita_medidas=True (RN-2).",
            )
        if fecha_medidas is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="fecha_medidas es obligatoria cuando solicita_medidas=True (RN-2).",
            )
    if verifica_medidas and fecha_verificacion is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha_verificacion es obligatoria cuando verifica_medidas=True (RN-4).",
        )


def validar_coherencia_medidas(
    fecha_reca: datetime.date,
    fecha_medidas: datetime.date | None,
    fecha_verificacion: datetime.date | None,
) -> None:
    """RN-3 CEPA-041: fecha_verificacion >= fecha_medidas >= fecha_reca."""
    if fecha_medidas is not None and fecha_medidas < fecha_reca:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"fecha_medidas ({fecha_medidas}) debe ser igual o posterior "
                f"a fecha_reca ({fecha_reca}) (RN-3)."
            ),
        )
    if fecha_verificacion is not None and fecha_medidas is not None:
        if fecha_verificacion < fecha_medidas:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"fecha_verificacion ({fecha_verificacion}) debe ser igual o posterior "
                    f"a fecha_medidas ({fecha_medidas}) (RN-3)."
                ),
            )


def validar_coherencia_cierre(
    estado: EstadoReintegro,
    fecha_reintegro: datetime.date | None,
    fecha_reca: datetime.date | None,
    alta_medica: bool,
    alta_psicologica: bool,
    tipo_alta: str | None,
    fecha_caso: datetime.date | None = None,
) -> None:
    """Valida las reglas de negocio del cierre del caso (CEPA-042 RN-1..4).

    - RN-1: estado=total exige fecha_reintegro.
    - RN-2: fecha_reintegro >= fecha_reca (cuando fecha_reca disponible)
            Y fecha_reintegro >= fecha_caso (cuando fecha_caso disponible).
    - RN-4: reintegro total requiere al menos una alta y tipo_alta.
    """
    if estado == EstadoReintegro.TOTAL:
        if fecha_reintegro is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="fecha_reintegro es obligatoria cuando estado=total (RN-1).",
            )
        if fecha_reca is not None and fecha_reintegro < fecha_reca:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"fecha_reintegro ({fecha_reintegro}) no puede ser anterior "
                    f"a fecha_reca ({fecha_reca}) (RN-2)."
                ),
            )
        if fecha_caso is not None and fecha_reintegro < fecha_caso:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"fecha_reintegro ({fecha_reintegro}) no puede ser anterior "
                    f"a fecha_caso ({fecha_caso}) (RN-2)."
                ),
            )
        if not alta_medica and not alta_psicologica:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para cerrar el caso se requiere al menos alta_medica o alta_psicologica (RN-4).",
            )
        if not tipo_alta:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tipo_alta es obligatorio para cerrar el caso (RN-4).",
            )
    # estado=parcial o pendiente: no hay restricciones adicionales aquí


# ── Operaciones con sesión ────────────────────────────────────────────────

def crear_caso_reintegro(db: Session, data: CasoReintegroCreate) -> CasoReintegro:
    """Crea el caso de reintegro vinculado al ingreso (CEPA-040)."""
    caso = CasoReintegro(
        ingreso_id=data.ingreso_id,
        rut=data.rut,
        nombre=data.nombre,
        tipo_derivacion=data.tipo_derivacion.value,
        fecha_caso=data.fecha_caso,
        sexo=data.sexo,
        edad=data.edad,
        region=data.region,
        comuna=data.comuna,
        rubro_empleador=data.rubro_empleador,
    )
    db.add(caso)
    db.flush()
    return caso


def actualizar_caso_reintegro(
    db: Session, caso: CasoReintegro, data: CasoReintegroUpdate
) -> CasoReintegro:
    """Actualización parcial de datos del caso (CEPA-040 CA-1)."""
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if campo == "tipo_derivacion" and valor is not None:
            setattr(caso, campo, valor.value if hasattr(valor, "value") else valor)
        else:
            setattr(caso, campo, valor)
    db.flush()
    return caso


def _obtener_caso_o_404(db: Session, caso_id: int) -> CasoReintegro:
    caso = db.get(CasoReintegro, caso_id)
    if caso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso de reintegro {caso_id} no encontrado.",
        )
    return caso


def crear_reca(db: Session, caso_id: int, data: RecaCreate) -> Reca:
    """Registra la RECA asociada al caso (CEPA-041).

    Valida:
    - Unicidad de numero_reca por caso (RN-1 CEPA-041).
    - Coherencia reca/medidas (validar_coherencia_reca + validar_coherencia_medidas).
    """
    caso = _obtener_caso_o_404(db, caso_id)

    # Unicidad numero_reca por caso (RN-1)
    existente = db.execute(
        select(Reca).where(
            Reca.caso_reintegro_id == caso_id,
            Reca.numero_reca == data.numero_reca,
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una RECA con número {data.numero_reca!r} en este caso (RN-1).",
        )

    validar_coherencia_reca(
        data.solicita_medidas,
        data.detalle_medidas,
        data.fecha_medidas,
        data.verifica_medidas,
        data.fecha_verificacion,
    )
    if data.fecha_medidas is not None:
        validar_coherencia_medidas(data.fecha_reca, data.fecha_medidas, data.fecha_verificacion)

    reca = Reca(
        caso_reintegro_id=caso.id,
        fecha_reca=data.fecha_reca,
        tipo_reca=data.tipo_reca.value,
        numero_reca=data.numero_reca,
        riesgos_calificados=data.riesgos_calificados,
        razon_social=data.razon_social,
        solicita_medidas=data.solicita_medidas,
        detalle_medidas=data.detalle_medidas,
        fecha_medidas=data.fecha_medidas,
        verifica_medidas=data.verifica_medidas,
        detalle_verificacion=data.detalle_verificacion,
        fecha_verificacion=data.fecha_verificacion,
    )
    db.add(reca)
    db.flush()
    return reca


def actualizar_reca(db: Session, reca: Reca, data: RecaUpdate) -> Reca:
    """Actualización parcial de la RECA (CEPA-041)."""
    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        if campo == "tipo_reca" and valor is not None:
            setattr(reca, campo, valor.value if hasattr(valor, "value") else valor)
        else:
            setattr(reca, campo, valor)
    # Re-validar tras actualización
    validar_coherencia_reca(
        reca.solicita_medidas,
        reca.detalle_medidas,
        reca.fecha_medidas,
        reca.verifica_medidas,
        reca.fecha_verificacion,
    )
    if reca.fecha_medidas is not None:
        validar_coherencia_medidas(
            reca.fecha_reca, reca.fecha_medidas, reca.fecha_verificacion
        )
    db.flush()
    return reca


def cerrar_caso_reintegro(
    db: Session, caso: CasoReintegro, data: CierreReintegroUpdate
) -> CasoReintegro:
    """Registra el estado de reintegro y el cierre del caso (CEPA-042).

    Obtiene la fecha_reca desde la RECA asociada (si existe) para la
    validación de coherencia temporal.
    """
    fecha_reca = caso.reca.fecha_reca if caso.reca else None
    validar_coherencia_cierre(
        estado=data.estado_reintegro,
        fecha_reintegro=data.fecha_reintegro,
        fecha_reca=fecha_reca,
        fecha_caso=caso.fecha_caso,
        alta_medica=data.alta_medica,
        alta_psicologica=data.alta_psicologica,
        tipo_alta=data.tipo_alta.value if data.tipo_alta else None,
    )
    caso.estado_reintegro = data.estado_reintegro.value
    caso.fecha_reintegro = data.fecha_reintegro
    caso.remitido_isl = data.remitido_isl
    caso.alta_medica = data.alta_medica
    caso.fecha_alta_medica = data.fecha_alta_medica
    caso.alta_psicologica = data.alta_psicologica
    caso.fecha_alta_psico = data.fecha_alta_psico
    caso.tipo_alta = data.tipo_alta.value if data.tipo_alta else None
    caso.observaciones = data.observaciones
    db.flush()
    return caso
