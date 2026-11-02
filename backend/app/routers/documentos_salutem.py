"""Biblioteca de SALUTEM del paciente, para los módulos Licencias, Fármacos y Controles.

    GET /api/v1/pacientes/{paciente_id}/documentos-salutem?relacion=licencia|receta
    GET /api/v1/pacientes/{paciente_id}/documentos-salutem/{archivo_id}/contenido

SALUTEM no informa la carpeta del archivo: `relacion` filtra por la relación DEDUCIDA de
la atención (ver `app.services.archivos_control.documentos_de_paciente`). El contenido
se pide a SALUTEM al abrirlo y no se guarda, como en los documentos de un control.
"""

from datetime import date, datetime
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.integrations.salutem.client import get_salutem_client
from app.integrations.salutem.errors import SalutemError
from app.models.paciente import Paciente
from app.services.archivos_control import documentos_de_paciente

router = APIRouter(prefix="/api/v1/pacientes", tags=["documentos-salutem"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


class DocumentoSalutemRead(BaseModel):
    """Un documento de la biblioteca de SALUTEM del paciente.

    `licencia` y `receta` NO son la carpeta de SALUTEM (la API no la entrega): dicen si
    el archivo se subió el día de una atención que indicó licencia o receta, o en los
    días siguientes (tope de 7). `fecha_atencion` es esa atención.
    """

    archivo_id: int
    nombre: str
    tipo: str | None
    fecha_creacion: datetime | None
    licencia: bool
    receta: bool
    fecha_atencion: date | None


def _paciente_o_404(db: Session, paciente_id: int) -> None:
    if db.get(Paciente, paciente_id) is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")


@router.get(
    "/{paciente_id}/documentos-salutem",
    response_model=list[DocumentoSalutemRead],
    dependencies=[Depends(_reader)],
)
def listar_documentos(
    paciente_id: int,
    relacion: Literal["licencia", "receta"] | None = Query(
        None, description="Solo los relacionados con una atención que indicó licencia o receta"
    ),
    db: Session = Depends(get_db),
) -> list[DocumentoSalutemRead]:
    _paciente_o_404(db, paciente_id)
    return [
        DocumentoSalutemRead(
            archivo_id=d.archivo_id, nombre=d.nombre, tipo=d.tipo, fecha_creacion=d.fecha_creacion,
            licencia=d.licencia, receta=d.receta, fecha_atencion=d.fecha_atencion,
        )
        for d in documentos_de_paciente(db, paciente_id, relacion)
    ]


@router.get(
    "/{paciente_id}/documentos-salutem/{archivo_id}/contenido",
    response_class=Response,
    dependencies=[Depends(_reader)],
)
def contenido_documento(
    paciente_id: int,
    archivo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """Pide el archivo a SALUTEM y lo entrega sin guardarlo (ni en BD ni en disco)."""
    _paciente_o_404(db, paciente_id)
    documento = next((d for d in documentos_de_paciente(db, paciente_id) if d.archivo_id == archivo_id), None)
    if documento is None:
        raise HTTPException(status_code=404, detail="El archivo no pertenece a este paciente")
    try:
        contenido = get_salutem_client().obtener_archivo(documento.persona_id, archivo_id)
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
