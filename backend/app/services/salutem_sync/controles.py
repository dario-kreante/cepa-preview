"""Controles médicos creados automáticamente desde las atenciones de SALUTEM.

Cada atención con estado "Atendido" de una especialidad de control (`Médico/a` y
`Primera consulta médica EP` por defecto; se configura en SALUTEM_ESPECIALIDADES_CONTROL)
que cae en la ventana de un ingreso es un control del CEPA con origen SALUTEM. Las demás
especialidades (psicología, EPT, evaluaciones de ingreso, gestión administrativa...)
quedan solo en la pestaña SALUTEM. Los campos del formulario se buscan por nombre en
cualquier sección de la atención. Correspondencia con el control:

- fecha_control      ← citaFecha
- semana_control     ← semanas desde fecha_ingreso (la semana 1 parte el día del ingreso)
- medico_tratante    ← profesionalNombre
- region_derivacion  ← región del paciente en SIGE (SALUTEM no la informa)
- proximo_control    ← la siguiente cita vigente de la persona en la copia de SALUTEM; sin
                       cita, el campo "Próximo control" ("15 días", "1 mes") contado
                       desde la atención, con proximo_agendado en False
- licencia           ← la indicación que menciona la licencia, o el campo "Indicación
                       de reposo" aunque no diga "licencia" ("Reposo por 15 días")
- tipo_reposo        ← el campo "Tipo de reposo" (Total/Parcial); si falta, lo que diga
                       el texto de la licencia. Solo se guarda si hay licencia (RN-1)
- gaf_tramo          ← el campo "GAF", que SALUTEM registra por tramo ("51-60")
- gaf                ← "GAF NN" escrito en el texto, cuando el médico anota el número
- observaciones      ← la evolución del tratamiento
- tiempo_estimado_tratamiento, proyeccion_reintegro, factores_riesgo
                     ← los campos "Tiempo estimado de tratamiento", "Proyección de
                       reintegro laboral" y "Factores de riesgo acogidos"
- estado_reca        ← no viene en SALUTEM: lo completa el CEPA y el sync no lo toca
"""

import calendar
import html
import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.config import get_settings
from app.domain.enums_controles import TipoLicencia, TipoReposo
from app.integrations.salutem.campos import campo, tramo_gaf
from app.integrations.salutem.licencias import (
    ClaseMencion,
    MencionLicencia,
    extraer_indicacion_reposo,
    extraer_licencia,
)
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.services.salutem_sync.alertas_control import ACTOR, alertar_control, resolver_alertas_control

ORIGEN = "SALUTEM"
ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
# Una cita anulada o a la que no asistió no es un próximo control.
_NO_VIGENTES = (int(EstadoCitaSalutem.ANULADO), int(EstadoCitaSalutem.NO_ASISTE))
_RE_GAF = re.compile(r"\bGAF\s*:?\s*(\d{1,3})\b", re.IGNORECASE)
_RE_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_PLAZO = re.compile(r"(\d{1,3})\s*(d[ií]as?|semanas?|mes(?:es)?)\b", re.IGNORECASE)


def es_control(atencion: SalutemAtencion) -> bool:
    c = atencion.contenido
    return (
        atencion.desaparecida_en is None
        and atencion.fecha_cita is not None
        and c.get("estadoCitaId") == ATENDIDO
        and str(c.get("especialidadNombre") or "").strip().casefold()
        in get_settings().salutem_especialidades_control_set
    )


def sincronizar_control(
    db: Session, atencion: SalutemAtencion, ingreso: Ingreso, *, hoy: date, cambio: bool = True
) -> None:
    """Crea, actualiza o elimina el control del ingreso que corresponde a esta atención.

    Si la atención deja de ser control (se anuló, desapareció o no es de Médico/a) su
    control se elimina, salvo que el CEPA ya le haya registrado la RECA. Al crear o
    actualizar, alerta si el médico emitió una licencia o una receta.
    """
    control = db.scalars(
        select(ControlMedico)
        .where(ControlMedico.ingreso_id == ingreso.id, ControlMedico.salutem_cita_id == atencion.cita_id)
        .order_by(ControlMedico.id)
    ).first()
    if not es_control(atencion):
        if control is not None and control.origen == ORIGEN and control.estado_reca is None:
            resolver_alertas_control(db, control.id)
            record_audit(db, actor=ACTOR, action="DELETE", entity="control_medico", entity_id=str(control.id))
            db.delete(control)
            db.flush()
        return
    campos = _campos(db, atencion, ingreso)
    creado = control is None
    # Un control que pasa a tener licencia (p. ej. porque el extractor ahora la reconoce)
    # también alerta, aunque la atención no haya cambiado en SALUTEM.
    gano_licencia = not creado and campos["tiene_licencia"] and not control.tiene_licencia
    if control is None:
        control = ControlMedico(ingreso_id=ingreso.id, origen=ORIGEN, salutem_cita_id=atencion.cita_id, **campos)
        db.add(control)
        db.flush()
        record_audit(db, actor=ACTOR, action="CREATE", entity="control_medico", entity_id=str(control.id))
    elif any(getattr(control, k) != v for k, v in campos.items()):
        for k, v in campos.items():
            setattr(control, k, v)
        db.flush()
        record_audit(db, actor=ACTOR, action="UPDATE", entity="control_medico", entity_id=str(control.id))
    if creado or cambio or gano_licencia:
        alertar_control(db, control, atencion.contenido, hoy)


def _campos(db: Session, atencion: SalutemAtencion, ingreso: Ingreso) -> dict[str, Any]:
    c = atencion.contenido
    fecha = atencion.fecha_cita
    proximo = _proxima_cita(db, atencion.persona_id, fecha)
    agendado = proximo is not None
    if proximo is None:
        proximo = _plazo(campo(c, "Próximo control"), fecha)
    licencia = _licencia(c, fecha)
    reposo = (campo(c, "Tipo de reposo") or "").casefold()
    if reposo not in {e.value for e in TipoReposo}:
        reposo = licencia.tipo_reposo if licencia else None
    return {
        "fecha_control": fecha,
        "semana_control": max(1, (fecha - ingreso.fecha_ingreso).days // 7 + 1),
        "medico_tratante": (_texto(c.get("profesionalNombre")) or "Sin profesional informado")[:160],
        "region_derivacion": ingreso.paciente.region[:80],
        "proximo_control": proximo,
        "proximo_agendado": agendado,
        "tiene_licencia": licencia is not None,
        "resumen_termino_lm": licencia.texto[:500] if licencia else None,
        "total_dias_lm": licencia.dias if licencia else None,
        "tipo_licencia": _si_valido(licencia.tipo_licencia, TipoLicencia) if licencia else None,
        "tipo_reposo": _si_valido(reposo, TipoReposo) if licencia else None,
        "gaf": _gaf(c),
        "gaf_tramo": tramo_gaf(campo(c, "GAF")),
        "observaciones": _evolucion(c),
        "tiempo_estimado_tratamiento": _recortar(campo(c, "Tiempo estimado de tratamiento"), 80),
        "proyeccion_reintegro": _recortar(campo(c, "Proyección de reintegro laboral"), 80),
        "factores_riesgo": _recortar(campo(c, "Factores de riesgo acogidos"), 500),
    }


def _recortar(valor: str | None, largo: int) -> str | None:
    return valor[:largo] if valor else None


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


def _plazo(texto: str | None, desde: date) -> date | None:
    """"15 días", "2 semanas", "1 mes" → la fecha contada desde la atención."""
    m = _RE_PLAZO.search(texto or "")
    if m is None:
        return None
    n, unidad = int(m.group(1)), m.group(2).casefold()
    if unidad.startswith("d"):
        return desde + timedelta(days=n)
    if unidad.startswith("s"):
        return desde + timedelta(weeks=n)
    meses = desde.month - 1 + n
    anio, mes = desde.year + meses // 12, meses % 12 + 1
    return date(anio, mes, min(desde.day, calendar.monthrange(anio, mes)[1]))


def _registros(contenido: dict[str, Any], seccion: str) -> list[Any]:
    valor = contenido.get(seccion) or []
    if isinstance(valor, dict):
        valor = [valor]
    return [v.get("registro") if isinstance(v, dict) else v for v in valor]


def _licencia(contenido: dict[str, Any], fecha: date) -> MencionLicencia | None:
    menciones = [
        *(extraer_licencia(r, fecha_atencion=fecha) for r in _registros(contenido, "indicaciones")),
        extraer_indicacion_reposo(campo(contenido, "Indicación de reposo"), fecha_atencion=fecha),
    ]
    for mencion in menciones:
        if mencion is not None and mencion.clase == ClaseMencion.LICENCIA:
            return mencion
    return None


def _gaf(contenido: dict[str, Any]) -> int | None:
    for seccion in ("indicaciones", "diagnostico", "evolucionTratamiento", "anamnesis"):
        for registro in _registros(contenido, seccion):
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
