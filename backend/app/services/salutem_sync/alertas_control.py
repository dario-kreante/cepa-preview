"""Alertas de licencia y receta emitidas en una atención médica de SALUTEM.

Si la atención es un control, la alerta apunta al control (caso_tipo control_medico).
Las demás atenciones médicas (Evaluación médica, Evaluación psiquiátrica…; se configura
en SALUTEM_ESPECIALIDADES_ALERTA) no crean control y la alerta apunta a la atención
(caso_tipo salutem_atencion, caso_id = cita de SALUTEM).

Se crean en la vinculación del sync, no en el job diario: llegan con el retraso del
sync (~5 min). Una por control y tipo para siempre: si el médico corrige la atención no
se repite, y si la encargada la resolvió no reaparece. Solo para controles recientes
(DIAS_NOVEDAD): `fria` y `backfill` re-vinculan todo, y sin este corte un despliegue
llenaría el panel con controles de hace meses.
"""

import zlib
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.config import clave_especialidad
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.domain.proyeccion_reintegro import opcion_alertable
from app.integrations.salutem.senales import certificado_reposo, tiene_receta
from app.models.alertas import AlertaNotif
from app.models.control_medico import ControlMedico
from app.services.alertas import _resolver_usuario
from app.services.alertas_cierre import ingreso_cerrado
from app.services.config_alertas import cargar_ventanas

ACTOR = "sistema:salutem-sync"  # el mismo de controles.py y vinculacion.py
CASO_TIPO = "control_medico"
CASO_ATENCION = "salutem_atencion"
DIAS_NOVEDAD = 14
TIPOS = (TipoAlerta.LICENCIA_EN_CONTROL.value, TipoAlerta.RECETA_EN_CONTROL.value)
TIPO_PROYECCION = TipoAlerta.PROYECCION_REINTEGRO.value
# El ambiente de capacitación de SALUTEM rellena los campos con este texto: no es una proyección.
_RELLENO_CAPACITACION = "antecedente de prueba"
_ABIERTAS = (EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value)


def alertar_control(db: Session, control: ControlMedico, contenido: dict[str, Any], hoy: date) -> int:
    """Crea las alertas que falten para este control. Devuelve cuántas creó."""
    senales = {
        TipoAlerta.LICENCIA_EN_CONTROL.value: bool(control.tiene_licencia) or certificado_reposo(contenido),
        TipoAlerta.RECETA_EN_CONTROL.value: tiene_receta(contenido),
    }
    # Si la atención ya alertó como "atención médica sin control" (p. ej. una Evaluación
    # médica que pasó a ser control al ampliar SALUTEM_ESPECIALIDADES_CONTROL), esos tipos
    # ya están alertados: no se repiten para el control.
    ya_alertados = (
        _tipos_alertados(db, CASO_ATENCION, control.salutem_cita_id)
        if control.salutem_cita_id is not None
        else set()
    )
    creadas = _crear_alertas(
        db, CASO_TIPO, control.id, control.ingreso_id, control.fecha_control, senales, hoy,
        ya_alertados=ya_alertados,
    )
    return creadas + alertar_proyeccion(db, control, hoy)


def alertar_atencion(
    db: Session, cita_id: int, ingreso_id: int, fecha: date, hay_licencia: bool,
    contenido: dict[str, Any], hoy: date,
) -> int:
    """Crea las alertas que falten para una atención médica que no es control."""
    senales = {
        TipoAlerta.LICENCIA_EN_CONTROL.value: hay_licencia or certificado_reposo(contenido),
        TipoAlerta.RECETA_EN_CONTROL.value: tiene_receta(contenido),
    }
    return _crear_alertas(db, CASO_ATENCION, cita_id, ingreso_id, fecha, senales, hoy)


def proyeccion_real(valor: str | None) -> str | None:
    """La proyección sin espacios sobrantes, o None si está vacía o es el relleno de capacitación."""
    texto = (valor or "").strip()
    if not texto or _RELLENO_CAPACITACION in clave_especialidad(texto):
        return None
    return texto


def huella_proyeccion(valor: str) -> int:
    """Huella estable del valor (sin tildes ni mayúsculas), que cabe en ``ventana_dias``.

    ``alerta_notif`` no tiene dónde guardar el texto: la huella distingue «una alerta por
    control y valor» sin agregar columnas. El texto se lee del control al listar.
    """
    return zlib.crc32(clave_especialidad(valor).encode("utf-8")) & 0x7FFFFFFF


def alertar_proyeccion(db: Session, control: ControlMedico, hoy: date) -> int:
    """Alerta «Proyección de reintegro registrada»: una por control y valor. Devuelve 1 si la creó.

    QA-010 (23-11-2026): solo alertan «Paciente con reintegro parcial» y «1, 2 y 3 semanas
    aproximadamente» (``opcion_alertable``); el resto de la lista de SALUTEM, el relleno y los
    vacíos no. Con otro valor que el de la alerta abierta (el médico corrigió la proyección) la
    anterior queda resuelta y, si el nuevo valor alerta, se avisa de nuevo. Un valor ya alertado
    antes (aunque se resolviera a mano) no reaparece.
    """
    valor = proyeccion_real(control.proyeccion_reintegro)
    if opcion_alertable(valor) is None:
        valor = None
    huella = huella_proyeccion(valor) if valor is not None else None
    previas = db.scalars(
        select(AlertaNotif).where(
            AlertaNotif.caso_tipo == CASO_TIPO,
            AlertaNotif.caso_id == control.id,
            AlertaNotif.tipo == TIPO_PROYECCION,
        )
    ).all()
    ahora = datetime.now(timezone.utc)
    for previa in previas:
        if previa.estado in _ABIERTAS and previa.ventana_dias != huella:
            previa.estado = EstadoAlerta.RESUELTA.value
            previa.resuelta_en = ahora
    if valor is None or any(p.ventana_dias == huella for p in previas):
        db.flush()
        return 0
    if control.fecha_control < hoy - timedelta(days=DIAS_NOVEDAD):
        return 0
    if ingreso_cerrado(db, control.ingreso_id):  # QA-011: un caso cerrado no genera alertas
        return 0
    if not cargar_ventanas(db).get(TIPO_PROYECCION, {}).get("activo", True):
        return 0
    db.add(
        AlertaNotif(
            tipo=TIPO_PROYECCION,
            estado=EstadoAlerta.PENDIENTE.value,
            caso_id=control.id,
            caso_tipo=CASO_TIPO,
            usuario_id=_resolver_usuario(control.ingreso_id, db),
            plazo_objetivo=datetime.combine(control.fecha_control, time.min, tzinfo=timezone.utc),
            ventana_dias=huella,
            email_enviado=False,
        )
    )
    db.flush()
    record_audit(db, actor=ACTOR, action="CREATE", entity="alerta_notif", entity_id=f"proyeccion:{control.id}")
    return 1


def _tipos_alertados(db: Session, caso_tipo: str, caso_id: int) -> set[str]:
    """Tipos de alerta de licencia/receta que ya existen para el caso (resueltas incluidas)."""
    return set(
        db.scalars(
            select(AlertaNotif.tipo).where(
                AlertaNotif.caso_tipo == caso_tipo,
                AlertaNotif.caso_id == caso_id,
                AlertaNotif.tipo.in_(TIPOS),
            )
        )
    )


def _crear_alertas(
    db: Session, caso_tipo: str, caso_id: int, ingreso_id: int, fecha: date,
    senales: dict[str, bool], hoy: date, ya_alertados: set[str] = frozenset(),
) -> int:
    if fecha < hoy - timedelta(days=DIAS_NOVEDAD) or not any(senales.values()):
        return 0
    if ingreso_cerrado(db, ingreso_id):  # QA-011: un caso cerrado no genera alertas
        return 0
    ventanas = cargar_ventanas(db)
    existentes = _tipos_alertados(db, caso_tipo, caso_id) | set(ya_alertados)
    creadas = 0
    for tipo, hay in senales.items():
        if not hay or tipo in existentes or not ventanas.get(tipo, {}).get("activo", True):
            continue
        db.add(
            AlertaNotif(
                tipo=tipo,
                estado=EstadoAlerta.PENDIENTE.value,
                caso_id=caso_id,
                caso_tipo=caso_tipo,
                usuario_id=_resolver_usuario(ingreso_id, db),
                plazo_objetivo=datetime.combine(fecha, time.min, tzinfo=timezone.utc),
                ventana_dias=0,
                email_enviado=False,
            )
        )
        creadas += 1
    if creadas:
        db.flush()
        prefijo = "control" if caso_tipo == CASO_TIPO else "atencion"
        record_audit(db, actor=ACTOR, action="CREATE", entity="alerta_notif", entity_id=f"{prefijo}:{caso_id}")
    return creadas


def resolver_alertas_control(db: Session, control_id: int, caso_tipo: str = CASO_TIPO) -> None:
    """Resuelve las alertas abiertas de un control (o atención) que dejó de existir."""
    ahora = datetime.now(timezone.utc)
    for alerta in db.scalars(
        select(AlertaNotif).where(
            AlertaNotif.caso_tipo == caso_tipo,
            AlertaNotif.caso_id == control_id,
            AlertaNotif.tipo.in_((*TIPOS, TIPO_PROYECCION)),
            AlertaNotif.estado != EstadoAlerta.RESUELTA.value,
        )
    ):
        alerta.estado = EstadoAlerta.RESUELTA.value
        alerta.resuelta_en = ahora
    db.flush()
