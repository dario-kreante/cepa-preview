"""Catálogo de profesionales armado desde la copia local de SALUTEM. No habla con SALUTEM.

SALUTEM no tiene endpoint de profesionales: cada cita y cada atención traen `profesionalId`
(estable), `profesionalNombre`, `especialidadNombre` y `sucursalNombre`. Este paso recorre
esas filas de la copia y deja en `profesional`:

- identidad: `salutem_profesional_id`. Un profesional existente sin id se adopta si su
  nombre coincide (sin tildes, sin mayúsculas, espacios colapsados);
- `especialidades` y `sucursales` (unión de nombres), `primera_atencion` / `ultima_atencion`
  (citas en estado Atendido) y `sincronizado_en`;
- `nombre`, cuando SALUTEM lo cambia. `activo` no se toca: una baja manual se respeta.

Después re-vincula los controles y fichas de SALUTEM que quedaron sin `profesional_id`
(porque la vinculación corrió antes de que el profesional existiera).

Con `desde` solo mira las filas cambiadas desde entonces y acumula sobre lo guardado
(unión, mínimo, máximo); con `desde=None` recorre toda la copia.
"""

import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.control_medico import ControlMedico
from app.models.ficha_clinica import FichaClinica
from app.models.profesional import Profesional
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.services.salutem_sync.alertas_control import ACTOR

ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
_LARGO_NOMBRE = 160
_LARGO_ESPECIALIDAD = 80


@dataclass
class ResultadoProfesionales:
    creados: int = 0
    actualizados: int = 0
    # Profesionales sin id de SALUTEM que se emparejaron por nombre.
    adoptados: int = 0
    # Controles y fichas que recibieron `profesional_id` en la re-vinculación.
    vinculados: int = 0
    errores: list[str] = field(default_factory=list)


@dataclass
class _Visto:
    """Lo que la copia dice de un profesional en esta pasada."""

    nombre: str = ""
    # Fecha de la fila de la que salió el nombre: manda el nombre más reciente.
    fecha_nombre: date | None = None
    especialidades: Counter = field(default_factory=Counter)
    sucursales: set[str] = field(default_factory=set)
    primera: date | None = None
    ultima: date | None = None


def normalizar_nombre(nombre: str) -> str:
    """Clave de comparación: sin tildes, en minúsculas y con los espacios colapsados."""
    base = unicodedata.normalize("NFD", nombre)
    sin_tildes = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.casefold().split())


def _texto(valor: Any, largo: int) -> str | None:
    if not isinstance(valor, str):
        return None
    limpio = " ".join(valor.split())
    return limpio[:largo] or None


def profesional_id_salutem(contenido: dict[str, Any]) -> int | None:
    try:
        return int(contenido.get("profesionalId"))
    except (TypeError, ValueError):
        return None


def profesional_de_salutem(db: Session, contenido: dict[str, Any]) -> int | None:
    """Id del catálogo para el `profesionalId` de una cita o atención, si ya existe."""
    pid = profesional_id_salutem(contenido)
    if pid is None:
        return None
    return db.scalar(select(Profesional.id).where(Profesional.salutem_profesional_id == pid))


def _acumular(vistos: dict[int, _Visto], contenido: dict[str, Any], fecha: date | None, estado: Any) -> None:
    pid = profesional_id_salutem(contenido)
    nombre = _texto(contenido.get("profesionalNombre"), _LARGO_NOMBRE)
    if pid is None or nombre is None:
        return
    visto = vistos.setdefault(pid, _Visto())
    if not visto.nombre or (fecha is not None and (visto.fecha_nombre is None or fecha >= visto.fecha_nombre)):
        visto.nombre, visto.fecha_nombre = nombre, fecha
    especialidad = _texto(contenido.get("especialidadNombre"), _LARGO_ESPECIALIDAD)
    if especialidad:
        visto.especialidades[especialidad] += 1
    sucursal = _texto(contenido.get("sucursalNombre"), _LARGO_ESPECIALIDAD)
    if sucursal:
        visto.sucursales.add(sucursal)
    if fecha is not None and estado == ATENDIDO:
        visto.primera = fecha if visto.primera is None else min(visto.primera, fecha)
        visto.ultima = fecha if visto.ultima is None else max(visto.ultima, fecha)


def _recorrer(db: Session, desde: datetime | None) -> dict[int, _Visto]:
    vistos: dict[int, _Visto] = {}
    for tabla in (SalutemCita, SalutemAtencion):
        consulta = select(tabla.contenido, tabla.fecha_cita).where(tabla.desaparecida_en.is_(None))
        if desde is not None:
            consulta = consulta.where(tabla.cambiado_en >= desde)
        for contenido, fecha in db.execute(consulta.execution_options(yield_per=500)):
            _acumular(vistos, contenido, fecha, contenido.get("estadoCitaId"))
    return vistos


def _unir(actuales: list[str] | None, nuevos: set[str]) -> list[str]:
    return sorted(set(actuales or []) | nuevos)


def _minimo(a: date | None, b: date | None) -> date | None:
    return b if a is None else a if b is None else min(a, b)


def _maximo(a: date | None, b: date | None) -> date | None:
    return b if a is None else a if b is None else max(a, b)


def sincronizar_profesionales(db: Session, ahora: datetime, desde: datetime | None) -> ResultadoProfesionales:
    resultado = ResultadoProfesionales()
    vistos = _recorrer(db, desde)
    if vistos:
        por_id = {
            p.salutem_profesional_id: p
            for p in db.scalars(select(Profesional).where(Profesional.salutem_profesional_id.is_not(None)))
        }
        # Candidatos a adopción: los que aún no tienen id de SALUTEM, por nombre normalizado.
        sin_id: dict[str, Profesional] = {}
        for p in db.scalars(select(Profesional).where(Profesional.salutem_profesional_id.is_(None)).order_by(Profesional.id)):
            sin_id.setdefault(normalizar_nombre(p.nombre), p)
        for pid, visto in sorted(vistos.items()):
            try:
                with db.begin_nested():
                    _aplicar(db, pid, visto, por_id, sin_id, ahora, resultado)
            except Exception as e:  # noqa: BLE001 — un profesional con datos raros no detiene a los demás
                resultado.errores.append(f"profesional {pid}: {type(e).__name__}: {e}")
    resultado.vinculados = _revincular(db, resultado.errores)
    db.commit()
    return resultado


def _aplicar(
    db: Session,
    pid: int,
    visto: _Visto,
    por_id: dict[int, Profesional],
    sin_id: dict[str, Profesional],
    ahora: datetime,
    resultado: ResultadoProfesionales,
) -> None:
    profesional = por_id.get(pid)
    if profesional is None:
        adoptado = sin_id.pop(normalizar_nombre(visto.nombre), None)
        if adoptado is not None:
            profesional = adoptado
            profesional.salutem_profesional_id = pid
            _datos(profesional, visto, ahora)
            db.flush()
            record_audit(db, actor=ACTOR, action="UPDATE", entity="profesional", entity_id=str(profesional.id))
            resultado.adoptados += 1
        else:
            profesional = Profesional(nombre=visto.nombre, origen="SALUTEM", activo=True, salutem_profesional_id=pid)
            _datos(profesional, visto, ahora)
            db.add(profesional)
            db.flush()
            record_audit(db, actor=ACTOR, action="CREATE", entity="profesional", entity_id=str(profesional.id))
            resultado.creados += 1
        por_id[pid] = profesional
        return

    antes = (profesional.nombre, profesional.especialidad, profesional.especialidades,
             profesional.sucursales, profesional.primera_atencion, profesional.ultima_atencion)
    # Solo los de origen SALUTEM siguen el nombre de SALUTEM; uno de SIGE adoptado conserva el suyo.
    if profesional.origen == "SALUTEM" and visto.nombre != profesional.nombre:
        choque = db.scalar(
            select(Profesional.id).where(Profesional.nombre == visto.nombre, Profesional.id != profesional.id)
        )
        if choque is not None:
            raise ValueError(f"el nombre {visto.nombre!r} ya lo usa otro profesional del catálogo")
        profesional.nombre = visto.nombre
    _datos(profesional, visto, ahora)
    despues = (profesional.nombre, profesional.especialidad, profesional.especialidades,
               profesional.sucursales, profesional.primera_atencion, profesional.ultima_atencion)
    if despues != antes:
        db.flush()
        record_audit(db, actor=ACTOR, action="UPDATE", entity="profesional", entity_id=str(profesional.id))
        resultado.actualizados += 1


def _datos(profesional: Profesional, visto: _Visto, ahora: datetime) -> None:
    """Suma lo visto a lo guardado. No toca `nombre`, `origen` ni `activo`."""
    profesional.especialidades = _unir(profesional.especialidades, set(visto.especialidades))
    profesional.sucursales = _unir(profesional.sucursales, visto.sucursales)
    profesional.primera_atencion = _minimo(profesional.primera_atencion, visto.primera)
    profesional.ultima_atencion = _maximo(profesional.ultima_atencion, visto.ultima)
    if not profesional.especialidad and visto.especialidades:
        # Más frecuente; en empate, la primera por orden alfabético.
        profesional.especialidad = min(visto.especialidades.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    profesional.sincronizado_en = ahora


def _revincular(db: Session, errores: list[str]) -> int:
    """Pone `profesional_id` en controles y fichas de SALUTEM que todavía no lo tienen."""
    ids = {
        pid: id_
        for pid, id_ in db.execute(
            select(Profesional.salutem_profesional_id, Profesional.id).where(
                Profesional.salutem_profesional_id.is_not(None)
            )
        )
    }
    vinculados = 0
    controles = db.execute(
        select(ControlMedico, SalutemAtencion.contenido)
        .join(SalutemAtencion, SalutemAtencion.cita_id == ControlMedico.salutem_cita_id)
        .where(ControlMedico.profesional_id.is_(None))
    ).all()
    fichas = db.execute(
        select(FichaClinica, FichaClinica.contenido).where(
            FichaClinica.salutem_cita_id.is_not(None), FichaClinica.profesional_id.is_(None)
        )
    ).all()
    for fila, contenido in [*controles, *fichas]:
        id_ = ids.get(profesional_id_salutem(contenido))
        if id_ is None:
            continue
        try:
            with db.begin_nested():
                fila.profesional_id = id_
                db.flush()
            vinculados += 1
        except Exception as e:  # noqa: BLE001
            errores.append(f"{fila.__tablename__} {fila.id}: {type(e).__name__}: {e}")
    return vinculados
