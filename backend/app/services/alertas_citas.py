"""Alertas que nacen de las citas de SALUTEM: inasistencia, y cierre de las que ya no aplican.

La inasistencia se crea en el sync de citas (no en el job diario). Una por cita para
siempre: si la encargada la resolvió no reaparece, y solo se avisa de las recientes
(DIAS_NOVEDAD) para que el backfill no llene el panel con inasistencias viejas.

`resolver_alertas_con_hora` cierra las alertas de control médico e inasistencia de un
paciente que ya tiene hora vigente en SALUTEM: el aviso cumplió su propósito.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendamiento.salutem import pacientes_con_hora_vigente
from app.audit.service import record_audit
from app.config import get_settings
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import AlertaNotif
from app.models.cita import Cita
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.services.alertas import _resolver_usuario
from app.services.salutem_sync.alertas_control import ACTOR, DIAS_NOVEDAD

CASO_TIPO_INASISTENCIA = "salutem_cita"
_ABIERTAS = (EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value)


def alertar_inasistencia(
    db: Session, *, salutem_cita_id: int, cita: Cita, hoy: date, ventanas: dict
) -> bool:
    """Crea la alerta de inasistencia de una cita si corresponde. True si la creó."""
    if cita.estado != "inasistencia":
        return False
    if cita.fecha < hoy - timedelta(days=DIAS_NOVEDAD):
        return False
    if not ventanas.get(TipoAlerta.INASISTENCIA.value, {}).get("activo", True):
        return False
    filtro = get_settings().citas_especialidades_reportes_set
    if filtro and (cita.especialidad or "").casefold() not in filtro:
        return False
    existe = db.scalar(
        select(AlertaNotif.id).where(
            AlertaNotif.tipo == TipoAlerta.INASISTENCIA.value,
            AlertaNotif.caso_tipo == CASO_TIPO_INASISTENCIA,
            AlertaNotif.caso_id == salutem_cita_id,
        )
    )
    if existe is not None:
        return False
    db.add(
        AlertaNotif(
            tipo=TipoAlerta.INASISTENCIA.value,
            estado=EstadoAlerta.PENDIENTE.value,
            caso_id=salutem_cita_id,
            caso_tipo=CASO_TIPO_INASISTENCIA,
            usuario_id=_resolver_usuario(cita.ingreso_id, db),
            plazo_objetivo=datetime.combine(cita.fecha, time.min, tzinfo=timezone.utc),
            ventana_dias=0,
            email_enviado=False,
        )
    )
    db.flush()
    record_audit(
        db, actor=ACTOR, action="CREATE", entity="alerta_notif",
        entity_id=f"cita:{salutem_cita_id}",
    )
    return True


def resolver_alertas_con_hora(db: Session, hoy: date, actor: str) -> int:
    """Resuelve las alertas abiertas de control médico e inasistencia de pacientes con hora vigente."""
    de_control = db.execute(
        select(AlertaNotif, Ingreso.paciente_id)
        .join(ControlMedico, ControlMedico.id == AlertaNotif.caso_id)
        .join(Ingreso, Ingreso.id == ControlMedico.ingreso_id)
        .where(
            AlertaNotif.tipo == TipoAlerta.CONTROL_MEDICO.value,
            AlertaNotif.caso_tipo == "control_medico",
            AlertaNotif.estado.in_(_ABIERTAS),
        )
    ).all()
    de_inasistencia = db.execute(
        select(AlertaNotif, Ingreso.paciente_id)
        .join(Cita, Cita.salutem_cita_id == AlertaNotif.caso_id)
        .join(Ingreso, Ingreso.id == Cita.ingreso_id)
        .where(
            AlertaNotif.tipo == TipoAlerta.INASISTENCIA.value,
            AlertaNotif.caso_tipo == CASO_TIPO_INASISTENCIA,
            AlertaNotif.estado.in_(_ABIERTAS),
        )
    ).all()
    filas = [*de_control, *de_inasistencia]
    if not filas:
        return 0
    con_hora = pacientes_con_hora_vigente(db, {pid for _, pid in filas}, hoy)
    ahora = datetime.now(timezone.utc)
    resueltas = 0
    for alerta, paciente_id in filas:
        if paciente_id in con_hora:
            alerta.estado = EstadoAlerta.RESUELTA.value
            alerta.resuelta_en = ahora
            resueltas += 1
    if resueltas:
        db.flush()
        record_audit(
            db, actor=actor, action="UPDATE", entity="alerta_notif",
            entity_id=f"hora-vigente:{resueltas}", valor_nuevo=EstadoAlerta.RESUELTA.value,
        )
    return resueltas
