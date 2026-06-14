"""Router de Gestión de Fármacos (EPIC-02).

Prefijo: /api/v1/registro-farmacologico
Sub-recursos: /esquema, /recetas, /seguimiento, /recetas/alertas/generar

IMPORTANTE: el endpoint POST /recetas/alertas/generar se registra ANTES de
/{ingreso_id}/* para evitar que FastAPI intente parsear "recetas" como entero.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.farmacos import (
    AlertaRead,
    EsquemaIndicacionBody,
    EsquemaIndicacionRead,
    RecetaBody,
    RecetaRead,
    RegistroFarmacologicoCreate,
    RegistroFarmacologicoRead,
    RegistroFarmacologicoUpdate,
    SeguimTratamientoBody,
    SeguimTratamientoRead,
)
from app.services.farmacos import (
    agregar_indicacion,
    actualizar_registro,
    crear_o_reactivar_registro,
    crear_receta,
    crear_seguimiento,
    generar_alertas_revision,
    listar_indicaciones,
    listar_recetas,
    listar_seguimientos,
    obtener_registro_por_ingreso,
)

router = APIRouter(prefix="/api/v1/registro-farmacologico", tags=["farmacos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── RegistroFarmacologico (CEPA-020) ──────────────────────────────────────────

@router.post(
    "",
    response_model=RegistroFarmacologicoRead,
    dependencies=[Depends(_writer)],
)
def crear_registro(
    payload: RegistroFarmacologicoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro, creado = crear_o_reactivar_registro(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE" if creado else "UPDATE",
        entity="reg_farmacologico",
        entity_id=str(registro.id),
    )
    db.commit()
    db.refresh(registro)
    # HTTP 201 si nuevo, 200 si reactivado
    from fastapi.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder

    if creado:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder(RegistroFarmacologicoRead.model_validate(registro)),
        )
    return registro


# ── Alertas de revisión (CEPA-022 RN-3) ──────────────────────────────────────
# IMPORTANTE: este endpoint debe registrarse ANTES de /{ingreso_id}/* para que
# FastAPI no intente resolver "recetas" como un entero de ingreso_id.

@router.post(
    "/recetas/alertas/generar",
    response_model=list[AlertaRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def generar_alertas_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Ejecuta el proceso de alertas de revisión próxima (ventana 5 días)."""
    alertas = generar_alertas_revision(db)
    for alerta in alertas:
        record_audit(
            db,
            actor=current_user.username,
            action="CREATE",
            entity="alerta",
            entity_id=str(alerta.id),
        )
    db.commit()
    for alerta in alertas:
        db.refresh(alerta)
    return alertas


# ── RegistroFarmacologico read/update (CEPA-020) ──────────────────────────────

@router.get(
    "/{ingreso_id}",
    response_model=RegistroFarmacologicoRead,
    dependencies=[Depends(_reader)],
)
def obtener_registro(ingreso_id: int, db: Session = Depends(get_db)):
    return obtener_registro_por_ingreso(db, ingreso_id)


@router.patch(
    "/{ingreso_id}",
    response_model=RegistroFarmacologicoRead,
    dependencies=[Depends(_writer)],
)
def actualizar(
    ingreso_id: int,
    payload: RegistroFarmacologicoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = actualizar_registro(db, ingreso_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="reg_farmacologico",
        entity_id=str(registro.id),
    )
    db.commit()
    db.refresh(registro)
    return registro


# ── EsquemaIndicacion (CEPA-021) ──────────────────────────────────────────────

@router.post(
    "/{ingreso_id}/esquema",
    response_model=EsquemaIndicacionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def agregar_indicacion_endpoint(
    ingreso_id: int,
    payload: EsquemaIndicacionBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    from app.schemas.farmacos import EsquemaIndicacionCreate as _EIC

    data = _EIC(
        registro_id=registro.id,
        medicamento=payload.medicamento,
        dosis=payload.dosis,
        frecuencia=payload.frecuencia,
        extra_sistema=payload.extra_sistema,
    )
    indicacion = agregar_indicacion(db, data)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="esquema_indicacion",
        entity_id=str(indicacion.id),
    )
    db.commit()
    db.refresh(indicacion)
    return indicacion


@router.get(
    "/{ingreso_id}/esquema",
    response_model=list[EsquemaIndicacionRead],
    dependencies=[Depends(_reader)],
)
def listar_indicaciones_endpoint(ingreso_id: int, db: Session = Depends(get_db)):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    return listar_indicaciones(db, registro.id)


# ── Receta (CEPA-022) ─────────────────────────────────────────────────────────

@router.post(
    "/{ingreso_id}/recetas",
    response_model=RecetaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_receta_endpoint(
    ingreso_id: int,
    payload: RecetaBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    from app.schemas.farmacos import RecetaCreate as _RC

    data = _RC(
        registro_id=registro.id,
        fecha_emision=payload.fecha_emision,
        fecha_revision=payload.fecha_revision,
        fecha_envio=payload.fecha_envio,
        marca_medicamento=payload.marca_medicamento,
    )
    receta = crear_receta(db, data)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="receta",
        entity_id=str(receta.id),
    )
    db.commit()
    db.refresh(receta)
    return receta


@router.get(
    "/{ingreso_id}/recetas",
    response_model=list[RecetaRead],
    dependencies=[Depends(_reader)],
)
def listar_recetas_endpoint(ingreso_id: int, db: Session = Depends(get_db)):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    return listar_recetas(db, registro.id)


# ── SeguimTratamiento (CEPA-023) ──────────────────────────────────────────────

@router.post(
    "/{ingreso_id}/seguimiento",
    response_model=SeguimTratamientoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_seguimiento_endpoint(
    ingreso_id: int,
    payload: SeguimTratamientoBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    from app.schemas.farmacos import SeguimTratamientoCreate as _STC

    data = _STC(
        registro_id=registro.id,
        disminucion_farmacos=payload.disminucion_farmacos,
        plan_disminucion=payload.plan_disminucion,
        cambio_esquema=payload.cambio_esquema,
        detalle_cambio=payload.detalle_cambio,
        observaciones=payload.observaciones,
    )
    seguim = crear_seguimiento(db, data)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="seguim_tratamiento",
        entity_id=str(seguim.id),
    )
    db.commit()
    db.refresh(seguim)
    return seguim


@router.get(
    "/{ingreso_id}/seguimiento",
    response_model=list[SeguimTratamientoRead],
    dependencies=[Depends(_reader)],
)
def listar_seguimientos_endpoint(ingreso_id: int, db: Session = Depends(get_db)):
    registro = obtener_registro_por_ingreso(db, ingreso_id)
    return listar_seguimientos(db, registro.id)
