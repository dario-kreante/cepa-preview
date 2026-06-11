from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.busqueda import Vista360
from app.schemas.ingreso import PacienteRead
from app.services.busqueda import buscar_pacientes, obtener_paciente, vista_360

router = APIRouter(prefix="/api/v1/pacientes", tags=["pacientes"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.get("/buscar", response_model=list[PacienteRead], dependencies=[Depends(_reader)])
def buscar(q: str, db: Session = Depends(get_db)) -> list[PacienteRead]:
    return buscar_pacientes(db, q)


@router.get("/{paciente_id}/vista-360", response_model=Vista360, dependencies=[Depends(_reader)])
def vista_360_endpoint(paciente_id: int, db: Session = Depends(get_db)) -> Vista360:
    paciente = obtener_paciente(db, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return vista_360(db, paciente)
