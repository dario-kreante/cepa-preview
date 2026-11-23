"""Sincroniza el catálogo de convenios de SALUTEM con la tabla ``convenio`` del CEPA.

Reglas:
- Se empareja por ``salutem_id``; si no hay, se adopta un convenio manual con el mismo nombre
  normalizado (sin tildes ni mayúsculas); si tampoco, se crea.
- Se actualizan ``nombre``, ``nombre_normalizado``, ``activo_salutem`` y ``sincronizado_en``.
  ``visible`` no se toca nunca, salvo al crear «Sin Convenio», que nace oculto.
- Los que tienen ``salutem_id`` y ya no vienen quedan con ``activo_salutem = False``. Nada se borra.
- Un renombre arrastra ``ingreso.tipo_convenio`` (que guarda el nombre) y deja una traza.
- No hace commit: lo hace quien llama.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.convenio import Convenio
from app.models.ingreso import Ingreso
from app.services.salutem_sync.alertas_control import ACTOR
from app.services.salutem_sync.profesionales import normalizar_nombre

_SIN_CONVENIO = "sin convenio"
_LARGO_NOMBRE = 120


@dataclass
class ResultadoConvenios:
    creados: int = 0
    actualizados: int = 0
    desactivados: int = 0
    renombrados: int = 0
    ingresos_renombrados: int = 0
    errores: list[str] = field(default_factory=list)


def _renombrar(db: Session, conv: Convenio, nuevo: str, actor: str, r: ResultadoConvenios) -> None:
    """Cambia el nombre y arrastra los ingresos que lo usaban (un UPDATE masivo, portable a Oracle)."""
    anterior = conv.nombre
    n = db.execute(
        update(Ingreso).where(Ingreso.tipo_convenio == anterior).values(tipo_convenio=nuevo)
    ).rowcount
    n = max(n or 0, 0)
    conv.nombre = nuevo
    r.renombrados += 1
    r.ingresos_renombrados += n
    record_audit(
        db,
        actor=actor,
        action="convenio_renombrado",
        entity="convenio",
        entity_id=str(conv.id),
        valor_anterior=anterior,
        valor_nuevo=f"{nuevo} ({n} ingresos)",
    )


def sincronizar_convenios(
    db: Session, cliente: SalutemClientProtocol, ahora: datetime, actor: str = ACTOR
) -> ResultadoConvenios:
    # Si SALUTEM está caído la excepción sube antes de tocar nada.
    entrantes = cliente.listar_convenios()
    r = ResultadoConvenios()

    existentes = list(db.scalars(select(Convenio)).all())
    por_sid = {c.salutem_id: c for c in existentes if c.salutem_id is not None}
    por_norm = {c.nombre_normalizado: c for c in existentes}
    vistos: set[int] = set()

    for ent in entrantes:
        nombre = " ".join(ent.nombre.split())
        norm = normalizar_nombre(nombre)
        # Aunque el nombre no sirva, SALUTEM sigue enviándolo: no es un convenio ausente.
        vistos.add(ent.salutem_id)
        if not norm or len(nombre) > _LARGO_NOMBRE:
            r.errores.append(f"convenio {ent.salutem_id}: nombre inválido o de más de {_LARGO_NOMBRE} caracteres")
            continue

        conv = por_sid.get(ent.salutem_id)
        if conv is None:
            otro = por_norm.get(norm)
            if otro is None:
                conv = Convenio(
                    nombre=nombre,
                    nombre_normalizado=norm,
                    salutem_id=ent.salutem_id,
                    activo_salutem=ent.activo,
                    visible=norm != _SIN_CONVENIO,
                    sincronizado_en=ahora,
                )
                db.add(conv)
                db.flush()
                por_sid[ent.salutem_id] = conv
                por_norm[norm] = conv
                r.creados += 1
                record_audit(
                    db, actor=actor, action="convenio_creado", entity="convenio",
                    entity_id=str(conv.id), valor_nuevo=nombre,
                )
            elif otro.salutem_id is None:
                # Un convenio manual con el mismo nombre: se adopta en vez de duplicarlo.
                otro.salutem_id = ent.salutem_id
                otro.activo_salutem = ent.activo
                otro.sincronizado_en = ahora
                if otro.nombre != nombre:
                    _renombrar(db, otro, nombre, actor, r)
                por_sid[ent.salutem_id] = otro
                r.actualizados += 1
            else:
                r.errores.append(f"convenio {ent.salutem_id}: el nombre «{nombre}» ya existe")
            continue

        # Ya existe: renombre y/o cambio de estado.
        otro = por_norm.get(norm)
        if otro is not None and otro is not conv:
            r.errores.append(f"convenio {ent.salutem_id}: el nombre «{nombre}» ya existe")
            continue
        cambio = False
        if conv.nombre != nombre:
            _renombrar(db, conv, nombre, actor, r)
            if conv.nombre_normalizado != norm:
                por_norm.pop(conv.nombre_normalizado, None)
                conv.nombre_normalizado = norm
                por_norm[norm] = conv
            cambio = True
        if conv.activo_salutem != ent.activo:
            conv.activo_salutem = ent.activo
            cambio = True
        conv.sincronizado_en = ahora
        if cambio:
            r.actualizados += 1

    for conv in existentes:
        if conv.salutem_id is not None and conv.salutem_id not in vistos and conv.activo_salutem:
            conv.activo_salutem = False
            conv.sincronizado_en = ahora
            r.desactivados += 1

    db.flush()
    return r
