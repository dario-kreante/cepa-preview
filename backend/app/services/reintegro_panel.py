"""Lista global de la pestaña Reintegro y precarga del alta de un caso (QA-010, 23-11-2026).

- ``panel_reintegro``: casos activos de todos los pacientes (con su proyección más reciente y sus
  pendientes) y «Pendientes por registrar»: pacientes con una alerta de proyección abierta y sin
  caso de reintegro activo.
- ``precarga_caso``: ocupación y tipo de trabajador para el alta, tomados de un caso anterior del
  mismo paciente o, para la ocupación, de la ficha de la persona en SALUTEM.
"""

import re
from typing import Any

from sqlalchemy import case, exists, select
from sqlalchemy.orm import Session

from app.agendamiento.salutem import lotes
from app.config import clave_especialidad
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.domain.proyeccion_reintegro import opcion_alertable, plazo_estimado
from app.domain.reintegro_enums import estado_solicitud_reca
from app.models.alertas import AlertaNotif
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro, Reca
from app.models.salutem_copia import SalutemPersona
from app.schemas.reintegro import (
    CasoPanelRead,
    PanelReintegroRead,
    PendienteRegistroRead,
    PrecargaCasoRead,
)
from app.services.reintegro import _ACTIVO
from app.services.reintegro_isl import ingreso_es_isl
from app.services.salutem_sync.alertas_control import proyeccion_real

_ABIERTAS = (EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value)


def _proyecciones_recientes(db: Session, ingreso_ids: set[int]) -> dict[int, tuple[str, Any]]:
    """Proyección más reciente (valor real, sin relleno) de los controles de cada ingreso."""
    resultado: dict[int, tuple[str, Any]] = {}
    for lote in lotes(ingreso_ids):
        filas = db.execute(
            select(ControlMedico.ingreso_id, ControlMedico.proyeccion_reintegro, ControlMedico.fecha_control)
            .where(ControlMedico.ingreso_id.in_(lote), ControlMedico.proyeccion_reintegro.is_not(None))
            .order_by(ControlMedico.fecha_control, ControlMedico.id)
        )
        for ingreso_id, valor, fecha in filas:
            if (real := proyeccion_real(valor)) is not None:
                resultado[ingreso_id] = (real, fecha)  # el último gana: orden ascendente
    return resultado


def _casos_activos(db: Session) -> list[CasoPanelRead]:
    filas = db.execute(
        select(
            CasoReintegro,
            Ingreso.paciente_id,
            Ingreso.folio,
            Paciente.nombre,
            Paciente.rut,
            # Sin booleanos en el SELECT: Oracle 19c no los tiene.
            case((ingreso_es_isl(), 1), else_=0),
            case((exists().where(Reca.caso_reintegro_id == CasoReintegro.id), 1), else_=0),
        )
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .join(Paciente, Paciente.id == Ingreso.paciente_id)
        .where(*_ACTIVO)
        .order_by(CasoReintegro.fecha_caso.desc(), CasoReintegro.id.desc())
    ).all()
    proyecciones = _proyecciones_recientes(db, {f[0].ingreso_id for f in filas})
    activos = []
    for caso, paciente_id, folio, nombre, rut, es_isl, con_reca in filas:
        proyeccion, fecha_proyeccion = proyecciones.get(caso.ingreso_id, (None, None))
        estado_reca = estado_solicitud_reca(caso.fecha_solicitud_reca, bool(con_reca))
        activos.append(
            CasoPanelRead(
                caso_id=caso.id,
                ingreso_id=caso.ingreso_id,
                paciente_id=paciente_id,
                paciente_nombre=nombre,
                rut=rut or caso.rut,
                folio=folio,
                estado_reintegro=caso.estado_reintegro,
                fecha_caso=caso.fecha_caso,
                proyeccion=proyeccion,
                fecha_proyeccion=fecha_proyeccion,
                es_isl=bool(es_isl),
                estado_solicitud_reca=estado_reca,
                reca_por_solicitar=bool(es_isl) and estado_reca.value == "pendiente",
                pendiente_remitir_isl=bool(es_isl) and not caso.remitido_isl,
            )
        )
    return activos


def _pendientes_registro(db: Session) -> list[PendienteRegistroRead]:
    """Pacientes con alerta de proyección abierta y sin caso activo: uno por paciente (el control
    más reciente)."""
    con_caso_activo = (
        select(Ingreso.paciente_id)
        .join(CasoReintegro, CasoReintegro.ingreso_id == Ingreso.id)
        .where(*_ACTIVO)
    )
    filas = db.execute(
        select(
            AlertaNotif.id,
            ControlMedico.proyeccion_reintegro,
            ControlMedico.fecha_control,
            Ingreso.id,
            Ingreso.folio,
            Paciente.id,
            Paciente.nombre,
            Paciente.rut,
        )
        .join(ControlMedico, ControlMedico.id == AlertaNotif.caso_id)
        .join(Ingreso, Ingreso.id == ControlMedico.ingreso_id)
        .join(Paciente, Paciente.id == Ingreso.paciente_id)
        .where(
            AlertaNotif.tipo == TipoAlerta.PROYECCION_REINTEGRO.value,
            AlertaNotif.caso_tipo == "control_medico",
            AlertaNotif.estado.in_(_ABIERTAS),
            Paciente.id.not_in(con_caso_activo),
        )
        .order_by(ControlMedico.fecha_control, AlertaNotif.id)
    ).all()
    por_paciente: dict[int, PendienteRegistroRead] = {}
    for alerta_id, valor, fecha, ingreso_id, folio, paciente_id, nombre, rut in filas:
        opcion = opcion_alertable(valor)
        por_paciente[paciente_id] = PendienteRegistroRead(
            paciente_id=paciente_id,
            paciente_nombre=nombre,
            rut=rut,
            ingreso_id=ingreso_id,
            folio=folio,
            alerta_id=alerta_id,
            proyeccion=opcion.texto if opcion is not None else valor,
            fecha_control=fecha,
            plazo_estimado=plazo_estimado(opcion, fecha) if opcion is not None else None,
        )
    return sorted(por_paciente.values(), key=lambda p: (p.fecha_control, p.alerta_id), reverse=True)


def panel_reintegro(db: Session) -> PanelReintegroRead:
    return PanelReintegroRead(activos=_casos_activos(db), pendientes_registro=_pendientes_registro(db))


# ── Precarga del alta ──────────────────────────────────────────────────────

# Claves de la ficha de SALUTEM que equivalen a la ocupación (comparadas sin tildes,
# mayúsculas ni separadores). SALUTEM no documenta una: se buscan las variantes habituales.
_CLAVES_OCUPACION = frozenset({"ocupacion", "profesion", "profesionuoficio", "profesionoficio", "oficio"})


def _clave(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", clave_especialidad(texto))


def ocupacion_de_contenido(contenido: dict | None) -> str | None:
    """La ocupación de la ficha de la persona en SALUTEM, si trae un campo equivalente."""
    if not isinstance(contenido, dict):
        return None
    for clave, valor in contenido.items():
        if _clave(str(clave)) in _CLAVES_OCUPACION and isinstance(valor, str) and valor.strip():
            return valor.strip()[:120]
    return None


def precarga_caso(db: Session, ingreso_id: int) -> PrecargaCasoRead:
    """Ocupación y tipo de trabajador para el alta del caso del ingreso.

    Primero el caso de reintegro más reciente del mismo paciente que los tenga (lo escribió una
    persona); si no, la ocupación de la ficha de SALUTEM. El ingreso no guarda ninguno de los dos.
    """
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        return PrecargaCasoRead()
    anteriores = db.scalars(
        select(CasoReintegro)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(Ingreso.paciente_id == ingreso.paciente_id)
        .order_by(CasoReintegro.fecha_caso.desc(), CasoReintegro.id.desc())
    ).all()
    ocupacion = next((c.ocupacion for c in anteriores if c.ocupacion), None)
    tipo_trabajador = next((c.tipo_trabajador for c in anteriores if c.tipo_trabajador), None)
    if ocupacion is None:
        paciente = db.get(Paciente, ingreso.paciente_id)
        if paciente is not None and paciente.salutem_persona_id is not None:
            persona = db.get(SalutemPersona, paciente.salutem_persona_id)
            ocupacion = ocupacion_de_contenido(persona.contenido if persona else None)
    return PrecargaCasoRead(ocupacion=ocupacion, tipo_trabajador=tipo_trabajador)
