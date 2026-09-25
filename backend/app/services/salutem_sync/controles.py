"""Controles médicos creados automáticamente desde las atenciones de SALUTEM.

Cada atención con estado "Atendido" que cae en la ventana de un ingreso es un control
del CEPA con origen SALUTEM. Correspondencia con el control:

- fecha_control      ← citaFecha
- semana_control     ← semanas desde fecha_ingreso (la semana 1 parte el día del ingreso)
- medico_tratante    ← profesionalNombre
- region_derivacion  ← región del paciente en SIGE (SALUTEM no la informa)
- proximo_control    ← la siguiente cita vigente de la persona en la copia de SALUTEM
- licencia y reposo  ← la indicación que menciona la licencia (extractor de licencias)
- gaf                ← "GAF NN" escrito en las indicaciones
- observaciones      ← la evolución del tratamiento
- estado_reca        ← no viene en SALUTEM: lo completa el CEPA y el sync no lo toca
"""

import html
import re
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums_controles import TipoLicencia, TipoReposo
from app.integrations.salutem.licencias import ClaseMencion, MencionLicencia, extraer_licencia
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.salutem_copia import SalutemAtencion, SalutemCita

ACTOR = "sistema:salutem-sync"
ORIGEN = "SALUTEM"
ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
# Una cita anulada o a la que no asistió no es un próximo control.
_NO_VIGENTES = (int(EstadoCitaSalutem.ANULADO), int(EstadoCitaSalutem.NO_ASISTE))
_RE_GAF = re.compile(r"\bGAF\s*:?\s*(\d{1,3})\b", re.IGNORECASE)
_RE_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")


def es_control(atencion: SalutemAtencion) -> bool:
    return atencion.desaparecida_en is None and atencion.contenido.get("estadoCitaId") == ATENDIDO


def sincronizar_control(db: Session, atencion: SalutemAtencion, ingreso: Ingreso) -> None:
    """Crea o actualiza el control del ingreso que corresponde a esta atención."""
    if atencion.fecha_cita is None:
        return
    control = db.scalars(
        select(ControlMedico)
        .where(ControlMedico.ingreso_id == ingreso.id, ControlMedico.salutem_cita_id == atencion.cita_id)
        .order_by(ControlMedico.id)
    ).first()
    campos = _campos(db, atencion, ingreso)
    if control is None:
        control = ControlMedico(ingreso_id=ingreso.id, origen=ORIGEN, salutem_cita_id=atencion.cita_id, **campos)
        db.add(control)
        db.flush()
        record_audit(db, actor=ACTOR, action="CREATE", entity="control_medico", entity_id=str(control.id))
        return
    if any(getattr(control, k) != v for k, v in campos.items()):
        for k, v in campos.items():
            setattr(control, k, v)
        db.flush()
        record_audit(db, actor=ACTOR, action="UPDATE", entity="control_medico", entity_id=str(control.id))


def _campos(db: Session, atencion: SalutemAtencion, ingreso: Ingreso) -> dict[str, Any]:
    c = atencion.contenido
    fecha = atencion.fecha_cita
    proximo = _proxima_cita(db, atencion.persona_id, fecha)
    licencia = _licencia(c, fecha)
    return {
        "fecha_control": fecha,
        "semana_control": max(1, (fecha - ingreso.fecha_ingreso).days // 7 + 1),
        "medico_tratante": (_texto(c.get("profesionalNombre")) or "Sin profesional informado")[:160],
        "region_derivacion": ingreso.paciente.region[:80],
        "proximo_control": proximo,
        "proximo_agendado": proximo is not None,
        "tiene_licencia": licencia is not None,
        "resumen_termino_lm": licencia.texto[:500] if licencia else None,
        "total_dias_lm": licencia.dias if licencia else None,
        "tipo_licencia": _si_valido(licencia.tipo_licencia, TipoLicencia) if licencia else None,
        "tipo_reposo": _si_valido(licencia.tipo_reposo, TipoReposo) if licencia else None,
        "gaf": _gaf(c),
        "observaciones": _evolucion(c),
    }


def _proxima_cita(db: Session, persona_id: int, fecha: date) -> date | None:
    return db.scalar(
        select(SalutemCita.fecha_cita)
        .where(
            SalutemCita.persona_id == persona_id,
            SalutemCita.fecha_cita > fecha,
            SalutemCita.desaparecida_en.is_(None),
            SalutemCita.estado_id.not_in(_NO_VIGENTES),
        )
        .order_by(SalutemCita.fecha_cita)
        .limit(1)
    )


def _registros(contenido: dict[str, Any], campo: str) -> list[Any]:
    valor = contenido.get(campo) or []
    if isinstance(valor, dict):
        valor = [valor]
    return [v.get("registro") if isinstance(v, dict) else v for v in valor]


def _licencia(contenido: dict[str, Any], fecha: date) -> MencionLicencia | None:
    for registro in _registros(contenido, "indicaciones"):
        mencion = extraer_licencia(registro, fecha_atencion=fecha)
        if mencion is not None and mencion.clase == ClaseMencion.LICENCIA:
            return mencion
    return None


def _gaf(contenido: dict[str, Any]) -> int | None:
    for campo in ("indicaciones", "diagnostico", "evolucionTratamiento", "anamnesis"):
        for registro in _registros(contenido, campo):
            m = _RE_GAF.search(_plano(registro) or "")
            if m and 1 <= int(m.group(1)) <= 100:
                return int(m.group(1))
    return None


def _evolucion(contenido: dict[str, Any]) -> str | None:
    partes = [p for r in _registros(contenido, "evolucionTratamiento") if (p := _plano(r))]
    return "\n".join(partes) or None


def _plano(registro: Any) -> str | None:
    if not isinstance(registro, str):
        return None
    texto = _RE_TAG.sub("", _RE_BR.sub("\n", html.unescape(registro)))
    lineas = [linea.strip() for linea in texto.splitlines()]
    return "\n".join(linea for linea in lineas if linea) or None


def _texto(v: Any) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip() else None


def _si_valido(valor: str | None, enum: type) -> str | None:
    return valor if valor in {e.value for e in enum} else None
