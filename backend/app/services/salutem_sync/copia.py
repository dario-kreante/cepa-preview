"""Guardado en la copia local de SALUTEM con detección de cambios por hash.

Cada función hace `flush` al terminar: SessionLocal usa autoflush=False y el
barrido consulta en el mismo día registros que acaba de agregar.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, PersonaSalutem
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.services.salutem_sync.hash import hash_contenido
from app.services.salutem_sync.tipos import Resultado
from app.util.rut import RutInvalidoError, normalizar_rut


def _rut_cepa(identificacion: str | None) -> str | None:
    if not identificacion:
        return None
    try:
        return normalizar_rut(identificacion)
    except RutInvalidoError:
        return None


def _fecha_creacion(crudo: dict[str, Any]) -> datetime | None:
    valor = crudo.get("citaFechaCreacion")
    if not isinstance(valor, str):
        return None
    try:
        return datetime.strptime(valor[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _guardar(
    db: Session,
    modelo: type,
    clave: int,
    contenido: dict[str, Any],
    campos: dict[str, Any],
    ahora: datetime,
) -> Resultado:
    nuevo_hash = hash_contenido(contenido)
    fila = db.get(modelo, clave)
    if fila is None:
        db.add(
            modelo(
                **campos,
                contenido=contenido,
                hash_contenido=nuevo_hash,
                visto_primera_vez=ahora,
                visto_ultima_vez=ahora,
                cambiado_en=ahora,
            )
        )
        db.flush()
        return Resultado.NUEVO

    fila.visto_ultima_vez = ahora
    reaparecio = getattr(fila, "desaparecida_en", None) is not None
    if fila.hash_contenido == nuevo_hash and not reaparecio:
        db.flush()
        return Resultado.IGUAL

    for nombre, valor in campos.items():
        setattr(fila, nombre, valor)
    fila.contenido = contenido
    fila.hash_contenido = nuevo_hash
    fila.cambiado_en = ahora
    if reaparecio:
        fila.desaparecida_en = None
        if hasattr(fila, "hash_vinculado"):
            # Con el mismo hash la vinculación no la vería: hay que forzarla.
            fila.hash_vinculado = None
    db.flush()
    return Resultado.CAMBIADO


def guardar_persona(db: Session, persona: PersonaSalutem, ahora: datetime) -> Resultado:
    return _guardar(
        db,
        SalutemPersona,
        persona.salutem_id,
        persona.crudo,
        {"salutem_id": persona.salutem_id, "rut": _rut_cepa(persona.identificacion)},
        ahora,
    )


def guardar_cita(db: Session, cita: CitaSalutem, ahora: datetime) -> Resultado:
    return _guardar(
        db,
        SalutemCita,
        cita.cita_id,
        cita.crudo,
        {
            "cita_id": cita.cita_id,
            "persona_id": cita.persona_id,
            "fecha_cita": cita.fecha,
            "fecha_creacion": _fecha_creacion(cita.crudo),
            "estado_id": cita.estado_id,
        },
        ahora,
    )


def guardar_atencion(db: Session, atencion: AtencionSalutem, ahora: datetime) -> Resultado:
    return _guardar(
        db,
        SalutemAtencion,
        atencion.cita.cita_id,
        atencion.contenido,
        {
            "cita_id": atencion.cita.cita_id,
            "persona_id": atencion.cita.persona_id,
            "fecha_cita": atencion.cita.fecha,
        },
        ahora,
    )


def marcar_citas_desaparecidas(
    db: Session, fecha: date, vistas: set[int], ahora: datetime
) -> int:
    """Marca las citas de `fecha` que no volvieron en un barrido completo de ese día."""
    filas = db.scalars(
        select(SalutemCita).where(
            SalutemCita.fecha_cita == fecha, SalutemCita.desaparecida_en.is_(None)
        )
    ).all()
    marcadas = 0
    for fila in filas:
        if fila.cita_id not in vistas:
            fila.desaparecida_en = ahora
            marcadas += 1
    db.flush()
    return marcadas


def marcar_atencion_desaparecida(db: Session, cita_id: int, ahora: datetime) -> bool:
    fila = db.get(SalutemAtencion, cita_id)
    if fila is None or fila.desaparecida_en is not None:
        return False
    fila.desaparecida_en = ahora
    fila.hash_vinculado = None
    db.flush()
    return True
