"""Lógica de negocio del módulo EPT (EPIC-03).

Reglas de negocio clave:
- RN-4 (CEPA-030): máx. 2 contactos por caso EPT.
- RN-5 (CEPA-030): corresponde_ept=False -> estado no_corresponde.
- RN-4 (CEPA-031): plazos no pueden ser anteriores a fecha_ingreso_ept.
- RN-2 (CEPA-031): testigos=True exige cantidad ≥ 1; testigos=False fuerza cantidad=0.
- RN-3 (CEPA-031): num_entrevistas ≥ 0.
- RN-3 (CEPA-032): fecha_entrega_isl no puede ser anterior a fecha_ingreso_ept ni a plazo_informe_ept.
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums_ept import EstadoCumplimiento, EstadoEpt
from app.models.ept import CasoEpt, ContactoEpt, PlazoEpt, ProcesoEpt
from app.schemas.ept import (
    CasoEptCreate,
    CasoEptUpdate,
    ContactoEptCreate,
    PlazoEptCreate,
    PlazoEptUpdate,
    ProcesoEptCreate,
    ProcesoEptUpdate,
)

_MAX_CONTACTOS = 2


# ──────────────────────────────────────────
# CasoEpt
# ──────────────────────────────────────────

def crear_caso_ept(db: Session, data: CasoEptCreate) -> CasoEpt:
    """Crea un caso EPT. Ajusta el estado si corresponde_ept=False (RN-5)."""
    estado = (
        EstadoEpt.NO_CORRESPONDE.value
        if not data.corresponde_ept
        else EstadoEpt.ABIERTO.value
    )
    caso = CasoEpt(
        ingreso_id=data.ingreso_id,
        mes=data.mes,
        fecha_ingreso_ept=data.fecha_ingreso_ept,
        nombre_trabajador=data.nombre_trabajador,
        rut_trabajador=data.rut_trabajador,
        region_trabajador=data.region_trabajador,
        eista=data.eista,
        factor_riesgo=data.factor_riesgo.value,
        corresponde_ept=data.corresponde_ept,
        estado=estado,
        razon_social=data.razon_social,
        unidad_cargo_horario=data.unidad_cargo_horario,
    )
    db.add(caso)
    db.flush()
    return caso


def actualizar_caso_ept(db: Session, caso: CasoEpt, data: CasoEptUpdate) -> CasoEpt:
    for campo, valor in data.model_dump(exclude_none=True).items():
        if campo == "factor_riesgo" and valor is not None:
            valor = valor.value if hasattr(valor, "value") else valor
        if campo == "estado" and valor is not None:
            valor = valor.value if hasattr(valor, "value") else valor
        setattr(caso, campo, valor)
    # si se cambia corresponde_ept a False, actualizar estado
    if data.corresponde_ept is False:
        caso.estado = EstadoEpt.NO_CORRESPONDE.value
    db.flush()
    return caso


def obtener_caso_ept_o_404(db: Session, caso_id: int) -> CasoEpt:
    caso = db.execute(select(CasoEpt).where(CasoEpt.id == caso_id)).scalar_one_or_none()
    if caso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso EPT {caso_id} no encontrado.",
        )
    return caso


# ──────────────────────────────────────────
# ContactoEpt
# ──────────────────────────────────────────

def agregar_contacto_ept(db: Session, data: ContactoEptCreate) -> ContactoEpt:
    """Agrega un contacto de coordinación EPT. Máx. 2 por caso (RN-4 CEPA-030)."""
    count = db.execute(
        select(ContactoEpt).where(ContactoEpt.caso_ept_id == data.caso_ept_id)
    ).scalars().all()
    if len(count) >= _MAX_CONTACTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Máximo {_MAX_CONTACTOS} contactos de coordinación EPT por caso."
            ),
        )
    contacto = ContactoEpt(caso_ept_id=data.caso_ept_id, correo=str(data.correo))
    db.add(contacto)
    db.flush()
    return contacto


# ──────────────────────────────────────────
# ProcesoEpt
# ──────────────────────────────────────────

def _validar_proceso(data, fecha_ingreso_ept: date) -> None:
    """Valida reglas de negocio del proceso EPT (CEPA-031)."""
    if data.hay_testigos is True and data.testigos_cantidad is not None:
        if data.testigos_cantidad < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Si hay testigos, la cantidad debe ser ≥ 1 (CEPA-031 RN-2).",
            )
    if data.hay_testigos is False:
        # Se fuerza a 0 en el servicio; si el caller envía >0 con hay_testigos=False, se corrige.
        pass
    if data.num_entrevistas is not None and data.num_entrevistas < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El número de entrevistas debe ser ≥ 0 (CEPA-031 RN-3).",
        )
    for campo_fecha, nombre in [
        (data.plazo_evid_denunciante, "plazo_evid_denunciante"),
        (data.plazo_insumos_empresa, "plazo_insumos_empresa"),
    ]:
        if campo_fecha is not None and campo_fecha < fecha_ingreso_ept:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"{nombre} no puede ser anterior a la fecha de ingreso EPT "
                    f"({fecha_ingreso_ept}) (CEPA-031 RN-4)."
                ),
            )


def crear_proceso_ept(db: Session, data: ProcesoEptCreate, caso: CasoEpt) -> ProcesoEpt:
    if not caso.corresponde_ept:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El caso EPT tiene corresponde_ept=False; no aplica gestión del proceso.",
        )
    _validar_proceso(data, caso.fecha_ingreso_ept)
    cantidad = 0 if not data.hay_testigos else (data.testigos_cantidad or 0)
    proceso = ProcesoEpt(
        caso_ept_id=caso.id,
        plazo_evid_denunciante=data.plazo_evid_denunciante,
        plazo_insumos_empresa=data.plazo_insumos_empresa,
        hay_testigos=data.hay_testigos,
        testigos_cantidad=cantidad,
        num_entrevistas=data.num_entrevistas or 0,
        insumos_eista=data.insumos_eista,
        doc_incumplimiento=data.doc_incumplimiento,
        observaciones=data.observaciones,
    )
    db.add(proceso)
    db.flush()
    return proceso


def actualizar_proceso_ept(
    db: Session, proceso: ProcesoEpt, data: ProcesoEptUpdate, caso: CasoEpt
) -> ProcesoEpt:
    # aplicar hay_testigos antes de validar cantidad
    hay_testigos = data.hay_testigos if data.hay_testigos is not None else proceso.hay_testigos
    testigos_cantidad = (
        data.testigos_cantidad
        if data.testigos_cantidad is not None
        else proceso.testigos_cantidad
    )
    if not hay_testigos:
        testigos_cantidad = 0
    # validar con los valores resultantes
    from dataclasses import dataclass

    @dataclass
    class _Proxy:
        hay_testigos: bool
        testigos_cantidad: int
        num_entrevistas: int | None
        plazo_evid_denunciante: date | None
        plazo_insumos_empresa: date | None

    proxy = _Proxy(
        hay_testigos=hay_testigos,
        testigos_cantidad=testigos_cantidad,
        num_entrevistas=(
            data.num_entrevistas if data.num_entrevistas is not None else proceso.num_entrevistas
        ),
        plazo_evid_denunciante=(
            data.plazo_evid_denunciante
            if data.plazo_evid_denunciante is not None
            else proceso.plazo_evid_denunciante
        ),
        plazo_insumos_empresa=(
            data.plazo_insumos_empresa
            if data.plazo_insumos_empresa is not None
            else proceso.plazo_insumos_empresa
        ),
    )
    _validar_proceso(proxy, caso.fecha_ingreso_ept)

    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(proceso, campo, valor)
    proceso.hay_testigos = hay_testigos
    proceso.testigos_cantidad = testigos_cantidad
    db.flush()
    return proceso


# ──────────────────────────────────────────
# PlazoEpt
# ──────────────────────────────────────────

def calcular_estado_cumplimiento(
    fecha_objetivo: date | None,
    fecha_envio: date | None,
    hoy: date,
    ventana_alerta_dias: int = 7,
) -> EstadoCumplimiento:
    """Calcula el estado de cumplimiento de un plazo (CEPA-032 RN-1).

    ventana_alerta_dias: días antes del vencimiento para marcar 'por_vencer'.
    Este valor será configurable desde EPIC-10/11 (ver Notas de cierre).
    """
    if fecha_envio is not None:
        return EstadoCumplimiento.CUMPLIDO
    if fecha_objetivo is None:
        return EstadoCumplimiento.EN_PLAZO
    dias_restantes = (fecha_objetivo - hoy).days
    if dias_restantes < 0:
        return EstadoCumplimiento.VENCIDO
    if dias_restantes <= ventana_alerta_dias:
        return EstadoCumplimiento.POR_VENCER
    return EstadoCumplimiento.EN_PLAZO


def _validar_plazo(data, caso: CasoEpt) -> None:
    """Valida que fecha_entrega_isl no sea anterior a fecha_ingreso ni a plazo_informe (RN-3)."""
    if data.fecha_entrega_isl is not None:
        if data.fecha_entrega_isl < caso.fecha_ingreso_ept:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "fecha_entrega_isl no puede ser anterior a la fecha de ingreso EPT "
                    f"({caso.fecha_ingreso_ept}) (CEPA-032 RN-3)."
                ),
            )
        pi = getattr(data, "plazo_informe_ept", None)
        if pi is not None and data.fecha_entrega_isl < pi:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "fecha_entrega_isl no puede ser anterior a plazo_informe_ept "
                    f"({pi}) (CEPA-032 RN-3)."
                ),
            )


def crear_plazo_ept(db: Session, data: PlazoEptCreate, caso: CasoEpt) -> PlazoEpt:
    if not caso.corresponde_ept:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El caso EPT tiene corresponde_ept=False; no aplica gestión de plazos.",
        )
    _validar_plazo(data, caso)
    hoy = date.today()
    plazo = PlazoEpt(
        caso_ept_id=caso.id,
        plazo_informe_ept=data.plazo_informe_ept,
        plazo_portal_isl=data.plazo_portal_isl,
        fecha_entrega_isl=data.fecha_entrega_isl,
        estado_informe=calcular_estado_cumplimiento(
            data.plazo_informe_ept, None, hoy
        ).value,
        estado_entrega_isl=calcular_estado_cumplimiento(
            data.fecha_entrega_isl, None, hoy
        ).value,
    )
    db.add(plazo)
    db.flush()
    return plazo


def actualizar_plazo_ept(
    db: Session, plazo: PlazoEpt, data: PlazoEptUpdate, caso: CasoEpt
) -> PlazoEpt:
    # Construir estado final para validaciones
    fecha_entrega_final = (
        data.fecha_entrega_isl
        if data.fecha_entrega_isl is not None
        else plazo.fecha_entrega_isl
    )
    plazo_informe_final = (
        data.plazo_informe_ept
        if data.plazo_informe_ept is not None
        else plazo.plazo_informe_ept
    )

    from dataclasses import dataclass

    @dataclass
    class _PlazoProxy:
        fecha_entrega_isl: date | None
        plazo_informe_ept: date | None

    _validar_plazo(
        _PlazoProxy(
            fecha_entrega_isl=fecha_entrega_final,
            plazo_informe_ept=plazo_informe_final,
        ),
        caso,
    )

    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(plazo, campo, valor)

    hoy = date.today()
    # recalcular estados tras la actualización
    plazo.estado_informe = calcular_estado_cumplimiento(
        plazo.plazo_informe_ept, plazo.fecha_envio, hoy
    ).value
    plazo.estado_entrega_isl = calcular_estado_cumplimiento(
        plazo.fecha_entrega_isl, plazo.fecha_envio, hoy
    ).value
    db.flush()
    return plazo
