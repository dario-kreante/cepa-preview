"""Paso 3 del sync: espejo en `cita` de las citas SALUTEM de los pacientes del CEPA.

`salutem_cita` guarda todas las citas de SALUTEM; aquí solo pasan a `cita` las de
personas que cruzan con un paciente del CEPA y cuya fecha cae en la ventana de alguno de
sus ingresos. El upsert es por `salutem_cita_id`. No habla con SALUTEM.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.config import get_settings
from app.integrations.salutem.models import EstadoCitaSalutem
from app.agendamiento.salutem import lotes
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.profesional import SIN_PROFESIONAL_SALUTEM, Profesional
from app.models.salutem_copia import SalutemCita, SalutemPersona
from app.services.alertas_citas import alertar_inasistencia, resolver_alertas_con_hora
from app.services.config_alertas import cargar_ventanas
from app.services.ficha_clinica import _en_ventana_del_ingreso
from app.services.salutem_sync.filtro import cruce_con_paciente
from app.services.salutem_sync.incremental import hoy_en_santiago
from app.services.salutem_sync.tipos import a_utc

ACTOR = "sistema:salutem-sync"
DIAS_AGENDADA_ANTIGUA = 90
LOTE_COMMIT = 200
_MAX_ESPECIALIDAD = 80
_MAX_PROFESIONAL = 160

log = logging.getLogger("salutem_sync")

_ESTADOS = {
    EstadoCitaSalutem.ATENDIDO: "realizada",
    EstadoCitaSalutem.NO_ASISTE: "inasistencia",
    EstadoCitaSalutem.ANULADO: "anulada",
    EstadoCitaSalutem.AGENDADO: "agendada",
    EstadoCitaSalutem.AGENDADO_WEB: "agendada",
    EstadoCitaSalutem.CONFIRMADO: "agendada",
    EstadoCitaSalutem.CONFIRMADO_WEB: "agendada",
    EstadoCitaSalutem.CONFIRMADO_EMAIL: "agendada",
    EstadoCitaSalutem.RECEPCIONADO: "agendada",  # [CEPA, P7]
}


def estado_cita(estado_id: int | None) -> str | None:
    """Estado de `cita` para un estado de SALUTEM; None si es nulo o desconocido."""
    if estado_id is None:
        return None
    try:
        return _ESTADOS.get(EstadoCitaSalutem(estado_id))
    except ValueError:
        return None


@dataclass
class ResultadoCitas:
    creadas: int = 0
    actualizadas: int = 0
    eliminadas: int = 0
    estado_desconocido: int = 0
    sin_ingreso: int = 0
    ambiguas: int = 0
    agendadas_antiguas: int = 0
    alertas_inasistencia: int = 0
    alertas_resueltas: int = 0
    errores: list[str] = field(default_factory=list)

    def sumar(self, otro: "ResultadoCitas") -> None:
        self.creadas += otro.creadas
        self.actualizadas += otro.actualizadas
        self.eliminadas += otro.eliminadas
        self.estado_desconocido += otro.estado_desconocido
        self.sin_ingreso += otro.sin_ingreso
        self.ambiguas += otro.ambiguas
        self.alertas_inasistencia += otro.alertas_inasistencia
        self.alertas_resueltas += otro.alertas_resueltas


def _texto(contenido: dict | None, clave: str, maximo: int) -> str | None:
    valor = (contenido or {}).get(clave)
    if not isinstance(valor, str):
        return None
    valor = valor.strip()
    if not valor or valor == SIN_PROFESIONAL_SALUTEM:
        return None
    return valor[:maximo]


def _candidatas(db: Session, desde: datetime | None, corte: date) -> dict[int, set[int]]:
    """cita_id -> pacientes con los que cruza. Incluye las desaparecidas (sirven para borrar).

    Con `desde`, solo las citas cambiadas desde entonces o de pacientes con ingresos
    editados desde entonces. Los pacientes de cada cita se leen aparte y sin ese filtro,
    para que una cita que cruza con dos pacientes siga viéndose ambigua.
    """
    seleccion = (
        select(SalutemCita.cita_id)
        .join(SalutemPersona, SalutemPersona.salutem_id == SalutemCita.persona_id)
        .join(Paciente, cruce_con_paciente())
        .where(SalutemCita.fecha_cita >= corte)
    )
    if desde is not None:
        seleccion = seleccion.where(
            or_(
                SalutemCita.cambiado_en >= desde,
                Paciente.id.in_(select(Ingreso.paciente_id).where(Ingreso.updated_at >= desde)),
            )
        )
    ids = sorted(set(db.scalars(seleccion).all()))
    por_cita: dict[int, set[int]] = defaultdict(set)
    for lote in lotes(ids):
        pares = db.execute(
            select(SalutemCita.cita_id, Paciente.id)
            .join(SalutemPersona, SalutemPersona.salutem_id == SalutemCita.persona_id)
            .join(Paciente, cruce_con_paciente())
            .where(SalutemCita.cita_id.in_(lote))
        ).all()
        for cita_id, paciente_id in pares:
            por_cita[cita_id].add(paciente_id)
    return por_cita


def sincronizar_citas(db: Session, *, desde: datetime | None, ahora: datetime) -> ResultadoCitas:
    """Refleja en `cita` las citas SALUTEM de los pacientes del CEPA.

    `desde=None` revisa todo (backfill y arranque en frío). Con `desde`, revisa las citas
    cambiadas desde entonces y todas las de pacientes con ingresos creados o editados desde
    entonces (un ingreso nuevo puede traer citas antiguas).

    Cada cita va en su propio savepoint; se hace commit por lote y uno final.
    """
    ahora = a_utc(ahora)
    hoy = hoy_en_santiago(ahora)
    corte = get_settings().citas_salutem_desde_fecha
    resultado = ResultadoCitas()

    por_cita = _candidatas(db, desde, corte)
    unicas: dict[int, int] = {}
    for cita_id, pacientes in por_cita.items():
        if len(pacientes) > 1:
            resultado.ambiguas += 1
            log.warning("Cita %s cruza con %d pacientes del CEPA: se omite", cita_id, len(pacientes))
            continue
        unicas[cita_id] = next(iter(pacientes))

    ids = sorted(unicas)
    ingresos: dict[int, list[Ingreso]] = defaultdict(list)
    for lote in lotes(sorted(set(unicas.values()))):
        for ingreso in db.scalars(select(Ingreso).where(Ingreso.paciente_id.in_(lote))):
            ingresos[ingreso.paciente_id].append(ingreso)
    existentes: dict[int, Cita] = {}
    copias: dict[int, SalutemCita] = {}
    for lote in lotes(ids):
        for c in db.scalars(select(Cita).where(Cita.salutem_cita_id.in_(lote))):
            existentes[c.salutem_cita_id] = c
        for s in db.scalars(select(SalutemCita).where(SalutemCita.cita_id.in_(lote))):
            copias[s.cita_id] = s

    nombres = {
        n
        for s in copias.values()
        if (n := _texto(s.contenido, "profesionalNombre", _MAX_PROFESIONAL)) is not None
    }
    profesionales: dict[str, int] = {}
    for lote in lotes(sorted(nombres)):
        for p in db.scalars(select(Profesional).where(Profesional.nombre.in_(lote))):
            profesionales[p.nombre] = p.id

    for n, cita_id in enumerate(ids, start=1):
        parcial = ResultadoCitas()
        try:
            with db.begin_nested():
                _procesar(
                    db, copias[cita_id], ingresos[unicas[cita_id]], existentes.get(cita_id),
                    profesionales, corte, parcial,
                )
            resultado.sumar(parcial)
        except Exception as e:  # noqa: BLE001 — una cita mala no debe frenar al resto
            log.warning("Sync de la cita %s falló: %s: %s", cita_id, type(e).__name__, e)
            resultado.errores.append(f"cita {cita_id}: {type(e).__name__}: {e}")
        if n % LOTE_COMMIT == 0:
            db.commit()
    db.commit()

    ventanas = cargar_ventanas(db)
    for lote in lotes(ids):
        for cita in db.scalars(
            select(Cita).where(Cita.salutem_cita_id.in_(lote), Cita.estado == "inasistencia")
        ):
            if alertar_inasistencia(
                db, salutem_cita_id=cita.salutem_cita_id, cita=cita, hoy=hoy, ventanas=ventanas
            ):
                resultado.alertas_inasistencia += 1
    resultado.alertas_resueltas = resolver_alertas_con_hora(db, hoy, ACTOR)
    db.commit()

    limite = hoy - timedelta(days=DIAS_AGENDADA_ANTIGUA)
    resultado.agendadas_antiguas = len(
        db.scalars(
            select(Cita.id).where(
                Cita.origen == "SALUTEM", Cita.estado == "agendada", Cita.fecha < limite
            )
        ).all()
    )
    return resultado


def _procesar(
    db: Session,
    salutem: SalutemCita,
    ingresos: list[Ingreso],
    existente: Cita | None,
    profesionales: dict[str, int],
    corte: date,
    resultado: ResultadoCitas,
) -> None:
    fecha = salutem.fecha_cita
    candidatos = (
        []
        if fecha is None or fecha < corte
        else [i for i in ingresos if _en_ventana_del_ingreso(fecha, i)]
    )
    if salutem.desaparecida_en is not None or not candidatos:
        if existente is not None:
            _eliminar(db, existente)
            resultado.eliminadas += 1
        elif salutem.desaparecida_en is None and fecha is not None and fecha >= corte:
            resultado.sin_ingreso += 1
        return

    estado = estado_cita(salutem.estado_id)
    if estado is None:
        resultado.estado_desconocido += 1
        log.warning(
            "Cita %s con estado_id %r desconocido: no se importa", salutem.cita_id, salutem.estado_id
        )
        return

    ingreso = max(candidatos, key=lambda i: (i.fecha_ingreso, i.id))
    especialidad = _texto(salutem.contenido, "especialidadNombre", _MAX_ESPECIALIDAD)
    profesional = _texto(salutem.contenido, "profesionalNombre", _MAX_PROFESIONAL)
    nuevos = {
        "ingreso_id": ingreso.id,
        "estado": estado,
        "fecha": fecha,
        "origen": "SALUTEM",
        "especialidad": especialidad,
        "profesional_nombre": profesional,
        "profesional_id": profesionales.get(profesional) if profesional else None,
    }

    if existente is None:
        fila = Cita(salutem_cita_id=salutem.cita_id, **nuevos)
        db.add(fila)
        db.flush()
        _auditar(db, "CREATE", fila, valor_nuevo=estado)
        resultado.creadas += 1
        return

    anterior = existente.estado
    cambios = {k: v for k, v in nuevos.items() if getattr(existente, k) != v}
    if not cambios:
        return
    for k, v in cambios.items():
        setattr(existente, k, v)
    db.flush()
    _auditar(db, "UPDATE", existente, valor_anterior=anterior, valor_nuevo=estado)
    resultado.actualizadas += 1


def _eliminar(db: Session, fila: Cita) -> None:
    anterior = fila.estado
    cita_id = str(fila.id)
    db.delete(fila)
    db.flush()
    record_audit(
        db, actor=ACTOR, action="DELETE", entity="cita", entity_id=cita_id, valor_anterior=anterior
    )


def _auditar(
    db: Session,
    accion: str,
    fila: Cita,
    *,
    valor_anterior: str | None = None,
    valor_nuevo: str | None = None,
) -> None:
    record_audit(
        db, actor=ACTOR, action=accion, entity="cita", entity_id=str(fila.id),
        valor_anterior=valor_anterior, valor_nuevo=valor_nuevo,
    )
