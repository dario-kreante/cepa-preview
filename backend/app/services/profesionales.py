"""Catálogo de profesionales: alta, edición, activación e importación desde SALUTEM."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.control_medico import ControlMedico
from app.models.profesional import SIN_PROFESIONAL_SALUTEM, Profesional
from app.schemas.profesional import ProfesionalCreate, ProfesionalUpdate


def listar_profesionales(db: Session, *, solo_activos: bool = False) -> list[Profesional]:
    q = select(Profesional).order_by(Profesional.nombre)
    if solo_activos:
        q = q.where(Profesional.activo == true())
    return list(db.scalars(q))


def obtener_o_404(db: Session, profesional_id: int) -> Profesional:
    profesional = db.get(Profesional, profesional_id)
    if profesional is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesional no encontrado")
    return profesional


def _nombre_tomado(db: Session, nombre: str, excepto_id: int | None = None) -> bool:
    q = select(Profesional.id).where(Profesional.nombre == nombre)
    if excepto_id is not None:
        q = q.where(Profesional.id != excepto_id)
    return db.scalar(q) is not None


def _409_nombre() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail="Ya existe un profesional con ese nombre"
    )


def crear_profesional(db: Session, datos: ProfesionalCreate, actor: str, rol: str) -> Profesional:
    if _nombre_tomado(db, datos.nombre):
        raise _409_nombre()
    profesional = Profesional(
        nombre=datos.nombre, especialidad=datos.especialidad, origen="SIGE", activo=True
    )
    db.add(profesional)
    db.flush()
    record_audit(
        db, actor=actor, rol=rol, action="CREATE", entity="profesional",
        entity_id=str(profesional.id),
    )
    return profesional


def actualizar_profesional(
    db: Session, profesional_id: int, datos: ProfesionalUpdate, actor: str, rol: str
) -> Profesional:
    profesional = obtener_o_404(db, profesional_id)
    if datos.nombre is not None and datos.nombre != profesional.nombre:
        if _nombre_tomado(db, datos.nombre, excepto_id=profesional.id):
            raise _409_nombre()
        profesional.nombre = datos.nombre
    if "especialidad" in datos.model_fields_set:
        profesional.especialidad = datos.especialidad
    if datos.activo is not None:
        profesional.activo = datos.activo
    db.flush()
    record_audit(
        db, actor=actor, rol=rol, action="UPDATE", entity="profesional",
        entity_id=str(profesional.id),
    )
    return profesional


def importar_desde_salutem(db: Session, actor: str, rol: str) -> int:
    """Agrega los médicos tratantes de controles SALUTEM que aún no están en el catálogo.

    Idempotente: compara por nombre exacto. No reactiva ni modifica los que ya existen,
    así una baja hecha a mano se respeta. Retorna cuántos creó.
    """
    nombres = db.scalars(
        select(ControlMedico.medico_tratante)
        .where(
            ControlMedico.origen == "SALUTEM",
            ControlMedico.medico_tratante != SIN_PROFESIONAL_SALUTEM,
        )
        .distinct()
    ).all()
    existentes = set(db.scalars(select(Profesional.nombre)).all())
    nuevos = sorted({n.strip() for n in nombres if n and n.strip()} - existentes)
    for nombre in nuevos:
        profesional = Profesional(nombre=nombre, origen="SALUTEM", activo=True)
        db.add(profesional)
        db.flush()
        record_audit(
            db, actor=actor, rol=rol, action="CREATE", entity="profesional",
            entity_id=str(profesional.id),
        )
    return len(nuevos)
