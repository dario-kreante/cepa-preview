"""Lógica de negocio del módulo de Controles Médicos (EPIC-06).

Historias cubiertas:
- CEPA-060: crear control con cálculo automático de semana.
- CEPA-061: programar próximo control (reemplaza el vigente anterior).
- CEPA-062: actualizar licencia/GAF y RECA del control.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.schemas.control_medico import (
    ControlMedicoCreate,
    LicenciaUpdate,
    ProximoControlUpdate,
)
from app.services.semana_control import FechaControlInvalidaError, calcular_semana_control


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-060: Crear control
# ─────────────────────────────────────────────────────────────────────────────

def crear_control(db: Session, data: ControlMedicoCreate) -> ControlMedico:
    """Registra un nuevo control médico vinculado al ingreso.

    Calcula semana_control automáticamente a partir de la fecha_ingreso del
    Ingreso vinculado. Rechaza si fecha_control < fecha_ingreso.

    Raises:
        HTTPException 404: si ingreso_id no existe.
        HTTPException 422: si fecha_control < fecha_ingreso.
    """
    ingreso = db.execute(
        select(Ingreso).where(Ingreso.id == data.ingreso_id)
    ).scalar_one_or_none()
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un ingreso con id={data.ingreso_id}. "
                   "El control debe asociarse a un folio existente (RN-1 CEPA-060).",
        )

    try:
        semana = calcular_semana_control(
            fecha_ingreso=ingreso.fecha_ingreso,
            fecha_control=data.fecha_control,
        )
    except FechaControlInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    control = ControlMedico(
        ingreso_id=data.ingreso_id,
        fecha_control=data.fecha_control,
        semana_control=semana,
        medico_tratante=data.medico_tratante,
        region_derivacion=data.region_derivacion,
    )
    db.add(control)
    db.flush()
    return control


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-061: Programar próximo control
# ─────────────────────────────────────────────────────────────────────────────

def programar_proximo_control(
    db: Session, control_id: int, data: ProximoControlUpdate
) -> ControlMedico:
    """Programa el próximo control sobre un control existente.

    Valida que proximo_control sea posterior a fecha_control (RN-1).
    Si el folio ya tiene un próximo control vigente en otro registro,
    lo cierra/reemplaza poniendo proximo_control=None (RN-4 CEPA-061).

    Raises:
        HTTPException 404: si control_id no existe.
        HTTPException 422: si proximo_control <= fecha_control.
    """
    control = _get_control_o_404(db, control_id)

    if data.proximo_control <= control.fecha_control:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"El próximo control ({data.proximo_control}) debe ser posterior "
                f"a la fecha del control actual ({control.fecha_control}) (RN-1 CEPA-061)."
            ),
        )

    # Cerrar el próximo control vigente anterior del mismo folio (RN-4)
    _cerrar_proximo_control_anterior(db, ingreso_id=control.ingreso_id, excluir_id=control_id)

    control.proximo_control = data.proximo_control
    control.proximo_agendado = data.proximo_agendado
    db.flush()
    return control


def _cerrar_proximo_control_anterior(
    db: Session, ingreso_id: int, excluir_id: int
) -> None:
    """Pone proximo_control=None en el registro previo con próximo vigente (RN-4 CEPA-061)."""
    anteriores = db.execute(
        select(ControlMedico).where(
            ControlMedico.ingreso_id == ingreso_id,
            ControlMedico.id != excluir_id,
            ControlMedico.proximo_control.is_not(None),
        )
    ).scalars().all()
    for anterior in anteriores:
        anterior.proximo_control = None
        anterior.proximo_agendado = False
    if anteriores:
        db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# CEPA-062: Actualizar licencia y RECA
# ─────────────────────────────────────────────────────────────────────────────

def actualizar_licencia(
    db: Session, control_id: int, data: LicenciaUpdate
) -> ControlMedico:
    """Actualiza los campos de licencia médica y RECA de un control existente.

    La validación de obligatoriedad condicional (tiene_licencia=True → campos LM
    requeridos) ya la realizó el schema LicenciaUpdate; aquí solo persiste.

    Raises:
        HTTPException 404: si control_id no existe.
    """
    control = _get_control_o_404(db, control_id)

    control.tiene_licencia = data.tiene_licencia
    if data.tiene_licencia:
        control.resumen_termino_lm = data.resumen_termino_lm
        control.total_dias_lm = data.total_dias_lm
        control.tipo_licencia = data.tipo_licencia.value if data.tipo_licencia else None
        control.tipo_reposo = data.tipo_reposo.value if data.tipo_reposo else None
    else:
        # licencia=no: limpiar campos de licencia (CA-2 CEPA-062)
        control.resumen_termino_lm = None
        control.total_dias_lm = None
        control.tipo_licencia = None
        control.tipo_reposo = None

    # GAF, RECA y observaciones siempre editables (RN-5)
    control.gaf = data.gaf
    control.estado_reca = data.estado_reca.value if data.estado_reca else None
    control.observaciones = data.observaciones
    db.flush()
    return control


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_control_o_404(db: Session, control_id: int) -> ControlMedico:
    control = db.execute(
        select(ControlMedico).where(ControlMedico.id == control_id)
    ).scalar_one_or_none()
    if control is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un control médico con id={control_id}.",
        )
    return control


def obtener_controles_por_ingreso(db: Session, ingreso_id: int) -> list[ControlMedico]:
    """Lista todos los controles asociados a un ingreso/folio."""
    return list(
        db.execute(
            select(ControlMedico)
            .where(ControlMedico.ingreso_id == ingreso_id)
            .order_by(ControlMedico.fecha_control)
        ).scalars()
    )
