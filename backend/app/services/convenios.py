"""Catálogo de convenios: alta, edición, lista para reportes y sugerencia según el origen de SALUTEM."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.convenio import Convenio
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemPersona
from app.schemas.convenio import ConvenioCreate, ConvenioUpdate
from app.services.convenios_sync import ResultadoConvenios, sincronizar_convenios
from app.services.salutem_sync.profesionales import normalizar_nombre
from app.util.rut import RutInvalidoError, normalizar_rut

_ORIGENES_SIN_CONVENIO = {"sin origen", "sin convenio"}


def listar_convenios(db: Session, *, solo_seleccionables: bool = False) -> list[Convenio]:
    convenios = list(db.scalars(select(Convenio).order_by(Convenio.nombre)))
    if solo_seleccionables:
        # El catálogo es chico (< 100 filas): se filtra en Python.
        convenios = [c for c in convenios if c.seleccionable]
    return convenios


def validar_tipo_convenio(db: Session, nuevo: str | None, actual: str | None) -> None:
    """El convenio de un ingreso debe estar en el catálogo seleccionable.

    Se acepta vacío y el mismo valor que ya tenía el ingreso (un convenio antiguo fuera del
    catálogo no se pierde al editar otros campos).
    """
    if nuevo is None or nuevo == actual:
        return
    if any(c.nombre == nuevo for c in listar_convenios(db, solo_seleccionables=True)):
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"El convenio «{nuevo}» no está en el catálogo de convenios.",
    )


def nombres_para_reportes(db: Session) -> list[str]:
    """Todo el catálogo más los valores antiguos de ``ingreso.tipo_convenio`` que ya no están en él."""
    nombres = {c.nombre for c in db.scalars(select(Convenio))}
    usados = db.scalars(select(Ingreso.tipo_convenio).where(Ingreso.tipo_convenio.is_not(None)).distinct())
    nombres.update(u.strip() for u in usados if u and u.strip())
    return sorted(nombres, key=normalizar_nombre)


def _409_nombre() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un convenio con ese nombre")


def _nombre_tomado(db: Session, normalizado: str, excepto_id: int | None = None) -> bool:
    q = select(Convenio.id).where(Convenio.nombre_normalizado == normalizado)
    if excepto_id is not None:
        q = q.where(Convenio.id != excepto_id)
    return db.scalar(q) is not None


def crear_convenio(db: Session, datos: ConvenioCreate, actor: str, rol: str) -> Convenio:
    normalizado = normalizar_nombre(datos.nombre)
    if _nombre_tomado(db, normalizado):
        raise _409_nombre()
    convenio = Convenio(nombre=datos.nombre, nombre_normalizado=normalizado, visible=True, activo_salutem=True)
    db.add(convenio)
    db.flush()
    record_audit(
        db, actor=actor, rol=rol, action="convenio_creado", entity="convenio",
        entity_id=str(convenio.id), valor_nuevo=convenio.nombre,
    )
    return convenio


def actualizar_convenio(db: Session, convenio_id: int, datos: ConvenioUpdate, actor: str, rol: str) -> Convenio:
    convenio = db.get(Convenio, convenio_id)
    if convenio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convenio no encontrado")

    if datos.nombre is not None and datos.nombre != convenio.nombre:
        if convenio.salutem_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Este convenio se renombra en SALUTEM.",
            )
        normalizado = normalizar_nombre(datos.nombre)
        if _nombre_tomado(db, normalizado, excepto_id=convenio.id):
            raise _409_nombre()
        anterior = convenio.nombre
        # ``ingreso.tipo_convenio`` guarda el nombre: los ingresos del convenio lo siguen.
        db.execute(update(Ingreso).where(Ingreso.tipo_convenio == anterior).values(tipo_convenio=datos.nombre))
        convenio.nombre = datos.nombre
        convenio.nombre_normalizado = normalizado
        record_audit(
            db, actor=actor, rol=rol, action="convenio_renombrado", entity="convenio",
            entity_id=str(convenio.id), valor_anterior=anterior, valor_nuevo=datos.nombre,
        )

    if datos.visible is not None and datos.visible != convenio.visible:
        record_audit(
            db, actor=actor, rol=rol, action="convenio_visibilidad", entity="convenio",
            entity_id=str(convenio.id), valor_anterior=str(convenio.visible), valor_nuevo=str(datos.visible),
        )
        convenio.visible = datos.visible

    db.flush()
    return convenio


def actualizar_desde_salutem(db: Session, cliente: SalutemClientProtocol, actor: str) -> ResultadoConvenios:
    """Corre el sync del catálogo con el usuario como actor. No hace commit."""
    return sincronizar_convenios(db, cliente, datetime.now(timezone.utc), actor=actor)


def convenio_sugerido(db: Session, *, paciente_id: int | None, rut: str | None) -> Convenio | None:
    """Convenio que corresponde al ``origen`` de la persona en SALUTEM, si hay pareja seleccionable."""
    persona: SalutemPersona | None = None
    if paciente_id is not None:
        paciente = db.get(Paciente, paciente_id)
        if paciente is not None:
            if paciente.salutem_persona_id is not None:
                persona = db.scalar(
                    select(SalutemPersona).where(SalutemPersona.salutem_id == paciente.salutem_persona_id)
                )
            elif paciente.rut:
                # Sin vínculo con SALUTEM: se busca por el RUT del propio paciente.
                rut = paciente.rut
    if persona is None and rut:
        try:
            canonico = normalizar_rut(rut)
        except RutInvalidoError:
            return None
        persona = db.scalar(select(SalutemPersona).where(SalutemPersona.rut == canonico))
    if persona is None:
        return None

    origen = (persona.contenido or {}).get("origen")
    if not isinstance(origen, str):
        return None
    normalizado = normalizar_nombre(origen)
    if not normalizado or normalizado in _ORIGENES_SIN_CONVENIO:
        return None
    convenio = db.scalar(select(Convenio).where(Convenio.nombre_normalizado == normalizado))
    if convenio is None or not convenio.seleccionable:
        return None
    return convenio
