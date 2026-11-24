"""Router del módulo de Seguimiento de Reintegro — /api/v1/reintegros (EPIC-04)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.reintegro import (
    CasoReintegroCreate,
    CasoReintegroRead,
    CasoReintegroUpdate,
    CierreReintegroUpdate,
    PacienteConCasosRepetidosRead,
    PanelReintegroRead,
    PrecargaCasoRead,
    RecaCreate,
    RecaRead,
    RecaUpdate,
    RemisionIslUpdate,
    SolicitudRecaUpdate,
)
from app.services.reintegro import (
    _obtener_caso_o_404,
    actualizar_caso_reintegro,
    actualizar_reca,
    cerrar_caso_reintegro,
    crear_caso_reintegro,
    consulta_casos,
    crear_reca,
    listar_pacientes_con_casos_repetidos,
    registrar_remision_isl,
    registrar_solicitud_reca,
)
from app.services.reintegro_panel import panel_reintegro, precarga_caso

router = APIRouter(prefix="/api/v1/reintegros", tags=["reintegros"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── CEPA-040: Caso de reintegro ────────────────────────────────────────────

@router.post(
    "",
    response_model=CasoReintegroRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_caso(
    payload: CasoReintegroCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = crear_caso_reintegro(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


@router.get(
    "",
    response_model=list[CasoReintegroRead],
    dependencies=[Depends(_reader)],
)
def listar_casos(
    ingreso_id: int | None = Query(default=None),
    paciente_id: int | None = Query(default=None),
    solo_activos: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[CasoReintegroRead]:
    """Lista casos. `paciente_id` abarca todos los ingresos del paciente; `solo_activos`
    deja los que no están en reintegro total (QA-003)."""
    return list(db.scalars(consulta_casos(ingreso_id, paciente_id, solo_activos)))


@router.get(
    "/duplicados",
    response_model=list[PacienteConCasosRepetidosRead],
    dependencies=[Depends(_reader)],
)
def listar_duplicados(
    db: Session = Depends(get_db),
) -> list[PacienteConCasosRepetidosRead]:
    """Pacientes con más de un caso activo, para revisarlos a mano (solo lectura)."""
    return listar_pacientes_con_casos_repetidos(db)


@router.get(
    "/panel",
    response_model=PanelReintegroRead,
    dependencies=[Depends(_reader)],
)
def obtener_panel(db: Session = Depends(get_db)) -> PanelReintegroRead:
    """Lista global de la pestaña (QA-010): casos activos de todos los pacientes y pacientes con
    una proyección de reintegro alertada que aún no tienen caso."""
    return panel_reintegro(db)


@router.get(
    "/precarga",
    response_model=PrecargaCasoRead,
    dependencies=[Depends(_reader)],
)
def obtener_precarga(
    ingreso_id: int = Query(...),
    db: Session = Depends(get_db),
) -> PrecargaCasoRead:
    """Ocupación y tipo de trabajador para precargar el alta de un caso del ingreso (QA-010)."""
    return precarga_caso(db, ingreso_id)


@router.get(
    "/{caso_id}",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_reader)],
)
def obtener_caso(
    caso_id: int,
    db: Session = Depends(get_db),
) -> CasoReintegroRead:
    return _obtener_caso_o_404(db, caso_id)


@router.patch(
    "/{caso_id}",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def actualizar_caso(
    caso_id: int,
    payload: CasoReintegroUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = _obtener_caso_o_404(db, caso_id)
    caso = actualizar_caso_reintegro(db, caso, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso


# ── QA-003: solicitud de RECA ─────────────────────────────────────────────

@router.patch(
    "/{caso_id}/solicitud-reca",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def registrar_solicitud(
    caso_id: int,
    payload: SolicitudRecaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    """Registra o corrige la fecha en que se solicitó la RECA."""
    caso = _obtener_caso_o_404(db, caso_id)
    anterior = caso.fecha_solicitud_reca
    caso = registrar_solicitud_reca(db, caso, payload.fecha_solicitud_reca)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
        valor_anterior=f"fecha_solicitud_reca={anterior.isoformat()}" if anterior else None,
        valor_nuevo=f"fecha_solicitud_reca={caso.fecha_solicitud_reca.isoformat()}",
    )
    db.commit()
    db.refresh(caso)
    return caso


# ── QA-010: remisión a ISL sin cerrar el caso ─────────────────────────────

@router.patch(
    "/{caso_id}/remitido-isl",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def registrar_remision(
    caso_id: int,
    payload: RemisionIslUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    """Marca el caso «Remitido a ISL» con su fecha (o la corrige), sin cerrarlo."""
    caso = _obtener_caso_o_404(db, caso_id)
    anterior = caso.fecha_remitido_isl
    caso = registrar_remision_isl(db, caso, payload.fecha_remitido_isl)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
        valor_anterior=f"fecha_remitido_isl={anterior.isoformat()}" if anterior else None,
        valor_nuevo=f"fecha_remitido_isl={caso.fecha_remitido_isl.isoformat()}",
    )
    db.commit()
    db.refresh(caso)
    return caso


# ── CEPA-041: RECA y medidas correctivas ──────────────────────────────────

@router.post(
    "/{caso_id}/reca",
    response_model=RecaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear_reca_endpoint(
    caso_id: int,
    payload: RecaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecaRead:
    reca = crear_reca(db, caso_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="reca",
        entity_id=str(reca.id),
    )
    db.commit()
    db.refresh(reca)
    return reca


@router.get(
    "/{caso_id}/reca",
    response_model=RecaRead,
    dependencies=[Depends(_reader)],
)
def obtener_reca(
    caso_id: int,
    db: Session = Depends(get_db),
) -> RecaRead:
    caso = _obtener_caso_o_404(db, caso_id)
    if caso.reca is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El caso {caso_id} no tiene RECA registrada.",
        )
    return caso.reca


@router.patch(
    "/{caso_id}/reca",
    response_model=RecaRead,
    dependencies=[Depends(_writer)],
)
def actualizar_reca_endpoint(
    caso_id: int,
    payload: RecaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecaRead:
    caso = _obtener_caso_o_404(db, caso_id)
    if caso.reca is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El caso {caso_id} no tiene RECA registrada.",
        )
    reca = actualizar_reca(db, caso.reca, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="reca",
        entity_id=str(reca.id),
    )
    db.commit()
    db.refresh(reca)
    return reca


# ── CEPA-042: Cierre / reintegro ──────────────────────────────────────────

@router.patch(
    "/{caso_id}/cierre",
    response_model=CasoReintegroRead,
    dependencies=[Depends(_writer)],
)
def registrar_cierre(
    caso_id: int,
    payload: CierreReintegroUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CasoReintegroRead:
    caso = _obtener_caso_o_404(db, caso_id)
    caso = cerrar_caso_reintegro(db, caso, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="caso_reintegro",
        entity_id=str(caso.id),
    )
    db.commit()
    db.refresh(caso)
    return caso
