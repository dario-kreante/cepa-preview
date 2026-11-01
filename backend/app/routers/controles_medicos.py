"""Router de Controles Médicos — EPIC-06.

Endpoints:
    POST   /api/v1/controles-medicos                            → crear control (CEPA-060)
    GET    /api/v1/controles-medicos/por-ingreso/{ingreso_id}   → listar por folio
    GET    /api/v1/controles-medicos/{control_id}               → detalle
    PATCH  /api/v1/controles-medicos/{control_id}/proximo-control  → CEPA-061
    PATCH  /api/v1/controles-medicos/{control_id}/licencia         → CEPA-062
    PATCH  /api/v1/controles-medicos/{control_id}/evaluacion       → evaluación clínica
    GET    /api/v1/controles-medicos/{control_id}/archivos         → documentos de SALUTEM del control
    GET    /api/v1/controles-medicos/{control_id}/archivos/{archivo_id}/contenido → el archivo, bajo demanda
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.integrations.salutem.client import get_salutem_client
from app.integrations.salutem.errors import SalutemError
from app.schemas.control_medico import (
    ArchivoControlRead,
    ControlMedicoCreate,
    ControlMedicoRead,
    EvaluacionUpdate,
    LicenciaUpdate,
    ProximoControlUpdate,
)
from app.services.archivos_control import archivos_de_control, persona_de_control
from app.services.control_medico import (
    _get_control_o_404,
    actualizar_evaluacion,
    actualizar_licencia,
    crear_control,
    leer_control,
    leer_controles,
    obtener_controles_por_ingreso,
    programar_proximo_control,
)

router = APIRouter(prefix="/api/v1/controles-medicos", tags=["controles-medicos"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")


# ── CEPA-060: Crear control ───────────────────────────────────────────────────

@router.post(
    "",
    response_model=ControlMedicoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_writer)],
)
def crear(
    payload: ControlMedicoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = crear_control(db, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="control_medico",
        entity_id=str(control.id),
    )
    db.commit()
    db.refresh(control)
    return leer_control(db, control)


# ── Lectura ───────────────────────────────────────────────────────────────────

@router.get(
    "/por-ingreso/{ingreso_id}",
    response_model=list[ControlMedicoRead],
    dependencies=[Depends(_reader)],
)
def listar_por_ingreso(
    ingreso_id: int,
    db: Session = Depends(get_db),
) -> list[ControlMedicoRead]:
    return leer_controles(db, obtener_controles_por_ingreso(db, ingreso_id))


@router.get(
    "/{control_id}",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_reader)],
)
def detalle(
    control_id: int,
    db: Session = Depends(get_db),
) -> ControlMedicoRead:
    return leer_control(db, _get_control_o_404(db, control_id))


# ── CEPA-061: Próximo control ─────────────────────────────────────────────────

@router.patch(
    "/{control_id}/proximo-control",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_writer)],
)
def programar_proximo(
    control_id: int,
    payload: ProximoControlUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = programar_proximo_control(db, control_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="control_medico",
        entity_id=str(control_id),
    )
    db.commit()
    db.refresh(control)
    return leer_control(db, control)


# ── CEPA-062: Licencia y RECA ─────────────────────────────────────────────────

@router.patch(
    "/{control_id}/licencia",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_licencia_endpoint(
    control_id: int,
    payload: LicenciaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = actualizar_licencia(db, control_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="control_medico",
        entity_id=str(control_id),
    )
    db.commit()
    db.refresh(control)
    return leer_control(db, control)


# ── Evaluación clínica (ficha del CEPA) ───────────────────────────────────────

@router.patch(
    "/{control_id}/evaluacion",
    response_model=ControlMedicoRead,
    dependencies=[Depends(_writer)],
)
def actualizar_evaluacion_endpoint(
    control_id: int,
    payload: EvaluacionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlMedicoRead:
    control = actualizar_evaluacion(db, control_id, payload)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="control_medico",
        entity_id=str(control_id),
    )
    db.commit()
    db.refresh(control)
    return leer_control(db, control)


# ── Documentos de la biblioteca de SALUTEM ───────────────────────────────────

@router.get(
    "/{control_id}/archivos",
    response_model=list[ArchivoControlRead],
    dependencies=[Depends(_reader)],
)
def listar_archivos(control_id: int, db: Session = Depends(get_db)) -> list[ArchivoControlRead]:
    return archivos_de_control(db, _get_control_o_404(db, control_id))


@router.get(
    "/{control_id}/archivos/{archivo_id}/contenido",
    response_class=Response,
    dependencies=[Depends(_reader)],
)
def contenido_archivo(
    control_id: int,
    archivo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """Pide el archivo a SALUTEM y lo entrega sin guardarlo (ni en BD ni en disco)."""
    control = _get_control_o_404(db, control_id)
    if archivo_id not in {a.archivo_id for a in archivos_de_control(db, control)}:
        raise HTTPException(status_code=404, detail="El archivo no pertenece a este control")
    try:
        contenido = get_salutem_client().obtener_archivo(persona_de_control(db, control), archivo_id)
    except SalutemError as e:
        raise HTTPException(status_code=502, detail="SALUTEM no respondió") from e
    if contenido is None:
        raise HTTPException(status_code=404, detail="SALUTEM no entregó el contenido del archivo")
    record_audit(db, actor=current_user.username, action="READ", entity="salutem_archivo", entity_id=str(archivo_id))
    db.commit()
    return Response(
        content=contenido.datos,
        media_type=contenido.media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(contenido.nombre)}",
            # Contenido clínico: que no quede en cachés y que el navegador no adivine el tipo.
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
