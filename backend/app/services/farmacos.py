"""Servicios de dominio para EPIC-02 — Gestión de Fármacos.

Cubre: RegistroFarmacologico (CEPA-020), EsquemaIndicacion (CEPA-021),
Receta y alertas de revisión (CEPA-022), SeguimTratamiento (CEPA-023).
"""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.farmacos import (
    Alerta,
    EsquemaIndicacion,
    Receta,
    RegistroFarmacologico,
    SeguimTratamiento,
)
from app.models.ingreso import Ingreso
from app.schemas.farmacos import (
    EsquemaIndicacionCreate,
    RecetaCreate,
    RegistroFarmacologicoCreate,
    RegistroFarmacologicoUpdate,
    SeguimTratamientoCreate,
)

_VENTANA_ALERTA_DIAS = 5


# ── RegistroFarmacologico ─────────────────────────────────────────────────────

def _exigir_ingreso(db, ingreso_id: int) -> Ingreso:
    """Devuelve el ingreso o lanza 404 si no existe."""
    ingreso = db.execute(
        select(Ingreso).where(Ingreso.id == ingreso_id)
    ).scalar_one_or_none()
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingreso {ingreso_id} no encontrado.",
        )
    return ingreso


def crear_o_reactivar_registro(
    db, data: RegistroFarmacologicoCreate
) -> tuple[RegistroFarmacologico, bool]:
    """Crea un registro farmacológico o reactiva el existente (CEPA-020 RN-4).

    Devuelve (registro, creado): creado=True si es nuevo, False si fue reactivado.
    """
    _exigir_ingreso(db, data.ingreso_id)
    existente = db.execute(
        select(RegistroFarmacologico).where(
            RegistroFarmacologico.ingreso_id == data.ingreso_id
        )
    ).scalar_one_or_none()

    if existente is not None:
        # Reactivar: actualizar campos y marcar activo (RN-4)
        existente.medico_tratante = data.medico_tratante
        existente.estado_farmacologico = data.estado_farmacologico.value
        if data.antecedentes_previos is not None:
            existente.antecedentes_previos = data.antecedentes_previos
        if data.tratamiento_previo is not None:
            existente.tratamiento_previo = data.tratamiento_previo
        existente.activo = True
        db.flush()
        return existente, False

    registro = RegistroFarmacologico(
        ingreso_id=data.ingreso_id,
        medico_tratante=data.medico_tratante,
        estado_farmacologico=data.estado_farmacologico.value,
        antecedentes_previos=data.antecedentes_previos,
        tratamiento_previo=data.tratamiento_previo,
        activo=True,
    )
    db.add(registro)
    db.flush()
    return registro, True


def obtener_registro_por_ingreso(db, ingreso_id: int) -> RegistroFarmacologico:
    """Devuelve el registro farmacológico de un ingreso o lanza 404."""
    registro = db.execute(
        select(RegistroFarmacologico).where(
            RegistroFarmacologico.ingreso_id == ingreso_id
        )
    ).scalar_one_or_none()
    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe registro farmacológico para el ingreso {ingreso_id}.",
        )
    return registro


def actualizar_registro(
    db, ingreso_id: int, data: RegistroFarmacologicoUpdate
) -> RegistroFarmacologico:
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    for campo, valor in data.model_dump(exclude_none=True).items():
        setattr(registro, campo, valor if not hasattr(valor, "value") else valor.value)
    db.flush()
    return registro


# ── EsquemaIndicacion ─────────────────────────────────────────────────────────

def _exigir_registro(db, registro_id: int) -> RegistroFarmacologico:
    reg = db.execute(
        select(RegistroFarmacologico).where(RegistroFarmacologico.id == registro_id)
    ).scalar_one_or_none()
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro farmacológico {registro_id} no encontrado.",
        )
    return reg


def agregar_indicacion(db, data: EsquemaIndicacionCreate) -> EsquemaIndicacion:
    """Agrega nueva indicación al esquema. Las previas conservan su estado (RN-2 CEPA-021)."""
    _exigir_registro(db, data.registro_id)
    indicacion = EsquemaIndicacion(
        registro_id=data.registro_id,
        medicamento=data.medicamento,
        dosis=data.dosis,
        frecuencia=data.frecuencia.value,
        extra_sistema=data.extra_sistema,
        vigente=True,
    )
    db.add(indicacion)
    db.flush()
    return indicacion


def listar_indicaciones(db, registro_id: int) -> list[EsquemaIndicacion]:
    _exigir_registro(db, registro_id)
    return list(
        db.scalars(
            select(EsquemaIndicacion)
            .where(EsquemaIndicacion.registro_id == registro_id)
            .order_by(EsquemaIndicacion.id)
        )
    )


# ── Receta ────────────────────────────────────────────────────────────────────

def crear_receta(db, data: RecetaCreate) -> Receta:
    """Crea una receta vinculada al registro farmacológico (CEPA-022 RN-1)."""
    _exigir_registro(db, data.registro_id)
    receta = Receta(
        registro_id=data.registro_id,
        fecha_emision=data.fecha_emision,
        fecha_revision=data.fecha_revision,
        fecha_envio=data.fecha_envio,
        marca_medicamento=data.marca_medicamento,
    )
    db.add(receta)
    db.flush()
    return receta


def listar_recetas(db, registro_id: int) -> list[Receta]:
    _exigir_registro(db, registro_id)
    return list(
        db.scalars(
            select(Receta)
            .where(Receta.registro_id == registro_id)
            .order_by(Receta.id)
        )
    )


def generar_alertas_revision(db, hoy: date | None = None) -> list[Alerta]:
    """Genera alertas para recetas cuya fecha_revision cae dentro de los próximos
    _VENTANA_ALERTA_DIAS días (límite inclusivo). Omite recetas que ya tienen alerta
    del mismo tipo generada el mismo día (idempotente). CEPA-022 RN-3/CA-2/CA-3.
    """

    hoy = hoy or date.today()
    limite = hoy + timedelta(days=_VENTANA_ALERTA_DIAS)

    recetas_proximas = db.scalars(
        select(Receta).where(
            Receta.fecha_revision >= hoy,
            Receta.fecha_revision <= limite,
        )
    ).all()

    nuevas: list[Alerta] = []
    for receta in recetas_proximas:
        # Idempotencia: no duplicar alerta si ya existe para esta receta+tipo+día
        ya_existe = db.execute(
            select(Alerta).where(
                Alerta.receta_id == receta.id,
                Alerta.tipo == "revision_proxima",
            )
        ).scalar_one_or_none()
        if ya_existe is not None:
            continue
        dias_restantes = (receta.fecha_revision - hoy).days
        alerta = Alerta(
            receta_id=receta.id,
            tipo="revision_proxima",
            mensaje=(
                f"La receta #{receta.id} vence el {receta.fecha_revision.isoformat()} "
                f"({dias_restantes} día(s)). Revisar con el administrativo asignado."
            ),
            leida=False,
        )
        db.add(alerta)
        nuevas.append(alerta)
    db.flush()
    return nuevas


# ── SeguimTratamiento ─────────────────────────────────────────────────────────

def crear_seguimiento(db, data: SeguimTratamientoCreate) -> SeguimTratamiento:
    """Crea un registro de seguimiento de tratamiento (CEPA-023)."""
    _exigir_registro(db, data.registro_id)
    seguim = SeguimTratamiento(
        registro_id=data.registro_id,
        disminucion_farmacos=data.disminucion_farmacos,
        plan_disminucion=data.plan_disminucion,
        cambio_esquema=data.cambio_esquema,
        detalle_cambio=data.detalle_cambio,
        observaciones=data.observaciones,
    )
    db.add(seguim)
    db.flush()
    return seguim


def listar_seguimientos(db, registro_id: int) -> list[SeguimTratamiento]:
    _exigir_registro(db, registro_id)
    return list(
        db.scalars(
            select(SeguimTratamiento)
            .where(SeguimTratamiento.registro_id == registro_id)
            .order_by(SeguimTratamiento.id)
        )
    )
