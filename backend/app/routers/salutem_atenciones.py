"""Atenciones médicas de SALUTEM que no son control, para revisar sus alertas.

    GET /api/v1/salutem/atenciones/{cita_id}                                → la atención
    GET /api/v1/salutem/atenciones/{cita_id}/archivos                       → sus documentos
    GET /api/v1/salutem/atenciones/{cita_id}/archivos/{archivo_id}/contenido → el archivo

Las alertas de licencia o receta de una Evaluación médica o psiquiátrica apuntan a la
cita de SALUTEM (caso_tipo salutem_atencion): estos endpoints muestran lo que el médico
indicó y los documentos de la biblioteca, igual que para un control.
"""

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.integrations.salutem.client import get_salutem_client
from app.integrations.salutem.errors import SalutemError
from app.models.salutem_copia import SalutemAtencion
from app.schemas.control_medico import ArchivoControlRead
from app.services.archivos_control import archivos_de_atencion
from app.services.salutem_sync.controles import licencia_de_atencion

router = APIRouter(prefix="/api/v1/salutem/atenciones", tags=["salutem-atenciones"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


class AtencionSalutemRead(BaseModel):
    cita_id: int
    fecha: date | None
    especialidad: str | None
    profesional: str | None
    # Lo que el médico indicó sobre la licencia, si lo hay.
    indicacion_licencia: str | None


def _texto(v: object) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip() else None


def _atencion_o_404(db: Session, cita_id: int) -> SalutemAtencion:
    atencion = db.get(SalutemAtencion, cita_id)
    if atencion is None or atencion.desaparecida_en is not None:
        raise HTTPException(status_code=404, detail="Atención no encontrada")
    return atencion


@router.get("/{cita_id}", response_model=AtencionSalutemRead, dependencies=[Depends(_reader)])
def obtener_atencion(cita_id: int, db: Session = Depends(get_db)) -> AtencionSalutemRead:
    atencion = _atencion_o_404(db, cita_id)
    c = atencion.contenido
    licencia = licencia_de_atencion(c, atencion.fecha_cita) if atencion.fecha_cita else None
    return AtencionSalutemRead(
        cita_id=atencion.cita_id,
        fecha=atencion.fecha_cita,
        especialidad=_texto(c.get("especialidadNombre")),
        profesional=_texto(c.get("profesionalNombre")),
        indicacion_licencia=licencia.texto[:500] if licencia else None,
    )


@router.get(
    "/{cita_id}/archivos", response_model=list[ArchivoControlRead], dependencies=[Depends(_reader)]
)
def listar_archivos(cita_id: int, db: Session = Depends(get_db)) -> list[ArchivoControlRead]:
    return archivos_de_atencion(db, _atencion_o_404(db, cita_id))


@router.get(
    "/{cita_id}/archivos/{archivo_id}/contenido",
    response_class=Response,
    dependencies=[Depends(_reader)],
)
def contenido_archivo(
    cita_id: int,
    archivo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """Pide el archivo a SALUTEM y lo entrega sin guardarlo (ni en BD ni en disco)."""
    atencion = _atencion_o_404(db, cita_id)
    if archivo_id not in {a.archivo_id for a in archivos_de_atencion(db, atencion)}:
        raise HTTPException(status_code=404, detail="El archivo no pertenece a esta atención")
    try:
        contenido = get_salutem_client().obtener_archivo(atencion.persona_id, archivo_id)
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
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
