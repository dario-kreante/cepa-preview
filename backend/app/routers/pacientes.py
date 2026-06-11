from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.paciente import Paciente
from app.schemas.busqueda import Vista360
from app.schemas.ingreso import PacienteRead
from app.services.busqueda import buscar_pacientes, obtener_paciente, vista_360

router = APIRouter(prefix="/api/v1/pacientes", tags=["pacientes"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")
_writer = require_role("Administrativo", "Coordinacion")


class PacienteUpdateSchema(BaseModel):
    """Actualización de datos demográficos/contacto del paciente (CEPA-121 CA-1)."""

    nombre: str | None = None
    sexo: str | None = None
    edad: int | None = None
    region: str | None = None
    comuna: str | None = None
    telefono: str | None = None
    correo: str | None = None


@router.get("/buscar", response_model=list[PacienteRead], dependencies=[Depends(_reader)])
def buscar(q: str, db: Session = Depends(get_db)) -> list[PacienteRead]:
    """CA-1: búsqueda de paciente por RUT, nombre o folio."""
    return buscar_pacientes(db, q)


@router.get("/{paciente_id}", response_model=PacienteRead, dependencies=[Depends(_reader)])
def obtener_paciente_por_id(paciente_id: int, db: Session = Depends(get_db)) -> Paciente:
    """Obtiene un paciente por ID. 404 si no existe."""
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return paciente


@router.patch(
    "/{paciente_id}",
    response_model=PacienteRead,
    dependencies=[Depends(_writer)],
)
def actualizar_paciente(
    paciente_id: int,
    payload: PacienteUpdateSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Paciente:
    """Actualización de datos demográficos/contacto (no del RUT). Requiere escritura."""
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    for campo, valor in payload.model_dump(exclude_none=True).items():
        setattr(paciente, campo, valor)
    db.flush()
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="paciente",
        entity_id=str(paciente_id),
    )
    db.commit()
    db.refresh(paciente)
    return paciente


@router.get("/{paciente_id}/vista-360", response_model=Vista360, dependencies=[Depends(_reader)])
def vista_360_endpoint(paciente_id: int, db: Session = Depends(get_db)) -> Vista360:
    paciente = obtener_paciente(db, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return vista_360(db, paciente)
