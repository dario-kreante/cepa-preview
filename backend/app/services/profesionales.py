"""Catálogo de profesionales: alta, edición, activación e importación desde SALUTEM."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.control_medico import ControlMedico
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.profesional import SIN_PROFESIONAL_SALUTEM, Profesional
from app.schemas.profesional import (
    ActividadProfesionalRead,
    AtencionPorEspecialidad,
    AtencionProfesionalRead,
    ProfesionalCreate,
    ProfesionalUpdate,
)
from app.services.salutem_sync.profesionales import (
    ATENDIDO,
    ResultadoProfesionales,
    normalizar_nombre,
    sincronizar_profesionales,
)

# Cuántas atenciones recientes devuelve el detalle de actividad.
ULTIMAS = 20


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


def importar_desde_salutem(db: Session, actor: str, rol: str) -> ResultadoProfesionales:
    """Ejecuta el paso completo del sync: arma el catálogo desde la copia de SALUTEM.

    Recorre toda la copia (sin límite incremental), adopta por nombre a los profesionales
    sin id de SALUTEM y re-vincula controles y fichas. Idempotente; no reactiva a los dados
    de baja. Además agrega los médicos tratantes de controles SALUTEM que ninguna cita de la
    copia explica (controles anteriores a la copia local), comparando por nombre normalizado.
    """
    resultado = sincronizar_profesionales(db, datetime.now(timezone.utc), None)
    nombres = db.scalars(
        select(ControlMedico.medico_tratante)
        .where(
            ControlMedico.origen == "SALUTEM",
            ControlMedico.medico_tratante != SIN_PROFESIONAL_SALUTEM,
        )
        .distinct()
    ).all()
    existentes = {normalizar_nombre(n) for n in db.scalars(select(Profesional.nombre)).all()}
    nuevos: dict[str, str] = {}
    for nombre in sorted({n.strip() for n in nombres if n and n.strip()}):
        nuevos.setdefault(normalizar_nombre(nombre), nombre)
    for clave, nombre in nuevos.items():
        if clave in existentes:
            continue
        profesional = Profesional(nombre=nombre, origen="SALUTEM", activo=True)
        db.add(profesional)
        db.flush()
        record_audit(
            db, actor=actor, rol=rol, action="CREATE", entity="profesional",
            entity_id=str(profesional.id),
        )
        resultado.creados += 1
    return resultado


def actividad_de_profesional(db: Session, profesional_id: int) -> ActividadProfesionalRead:
    """Totales y últimas atenciones de un profesional. Solo lectura."""
    profesional = obtener_o_404(db, profesional_id)
    por_especialidad: Counter[str] = Counter()
    pacientes: set[int] = set()
    atenciones: list[AtencionProfesionalRead] = []
    filas = db.execute(
        select(FichaClinica.id, FichaClinica.contenido, FichaClinica.folio, Ingreso.id, Paciente.id, Paciente.nombre)
        .join(Ingreso, Ingreso.id == FichaClinica.ingreso_id)
        .join(Paciente, Paciente.id == Ingreso.paciente_id)
        .where(
            FichaClinica.profesional_id == profesional.id,
            FichaClinica.origen == "SALUTEM",
            FichaClinica.eliminada_en_origen.is_(None),
        )
        .execution_options(yield_per=500)
    )
    for ficha_id, contenido, folio, ingreso_id, paciente_id, paciente in filas:
        # Una cita agendada o anulada no es una atención realizada.
        if contenido.get("estadoCitaId") != ATENDIDO:
            continue
        especialidad = (contenido.get("especialidadNombre") or "").strip() or None
        if especialidad:
            por_especialidad[especialidad] += 1
        pacientes.add(paciente_id)
        atenciones.append(
            AtencionProfesionalRead(
                ficha_id=ficha_id, fecha=_fecha(contenido.get("citaFecha")), especialidad=especialidad,
                folio=folio, ingreso_id=ingreso_id, paciente_id=paciente_id, paciente=paciente,
            )
        )
    controles = db.execute(
        select(ControlMedico.id, Ingreso.paciente_id)
        .join(Ingreso, Ingreso.id == ControlMedico.ingreso_id)
        .where(ControlMedico.profesional_id == profesional.id)
    ).all()
    pacientes.update(paciente_id for _, paciente_id in controles)
    ultimas = sorted(atenciones, key=lambda a: (a.fecha or date.min, a.ficha_id), reverse=True)[:ULTIMAS]
    return ActividadProfesionalRead(
        profesional_id=profesional.id,
        total_atenciones=len(atenciones),
        atenciones_por_especialidad=[
            AtencionPorEspecialidad(especialidad=e, total=t)
            for e, t in sorted(por_especialidad.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        total_controles=len(controles),
        pacientes_distintos=len(pacientes),
        primera_atencion=profesional.primera_atencion,
        ultima_atencion=profesional.ultima_atencion,
        ultimas_atenciones=ultimas,
    )


def _fecha(valor: object) -> date | None:
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None
