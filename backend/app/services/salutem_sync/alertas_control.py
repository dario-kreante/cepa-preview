"""Alertas de licencia y receta emitidas en un control creado desde SALUTEM.

Se crean en la vinculación del sync, no en el job diario: llegan con el retraso del
sync (~5 min). Una por control y tipo para siempre: si el médico corrige la atención no
se repite, y si la encargada la resolvió no reaparece. Solo para controles recientes
(DIAS_NOVEDAD): `fria` y `backfill` re-vinculan todo, y sin este corte un despliegue
llenaría el panel con controles de hace meses.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.integrations.salutem.senales import certificado_reposo, tiene_receta
from app.models.alertas import AlertaNotif
from app.models.control_medico import ControlMedico
from app.services.alertas import _resolver_usuario
from app.services.config_alertas import cargar_ventanas

ACTOR = "sistema:salutem-sync"  # el mismo de controles.py y vinculacion.py
CASO_TIPO = "control_medico"
DIAS_NOVEDAD = 14
TIPOS = (TipoAlerta.LICENCIA_EN_CONTROL.value, TipoAlerta.RECETA_EN_CONTROL.value)


def alertar_control(db: Session, control: ControlMedico, contenido: dict[str, Any], hoy: date) -> int:
    """Crea las alertas que falten para este control. Devuelve cuántas creó."""
    if control.fecha_control < hoy - timedelta(days=DIAS_NOVEDAD):
        return 0
    senales = {
        TipoAlerta.LICENCIA_EN_CONTROL.value: bool(control.tiene_licencia) or certificado_reposo(contenido),
        TipoAlerta.RECETA_EN_CONTROL.value: tiene_receta(contenido),
    }
    if not any(senales.values()):
        return 0
    ventanas = cargar_ventanas(db)
    existentes = set(
        db.scalars(
            select(AlertaNotif.tipo).where(
                AlertaNotif.caso_tipo == CASO_TIPO,
                AlertaNotif.caso_id == control.id,
                AlertaNotif.tipo.in_(TIPOS),
            )
        )
    )
    creadas = 0
    for tipo, hay in senales.items():
        if not hay or tipo in existentes or not ventanas.get(tipo, {}).get("activo", True):
            continue
        db.add(
            AlertaNotif(
                tipo=tipo,
                estado=EstadoAlerta.PENDIENTE.value,
                caso_id=control.id,
                caso_tipo=CASO_TIPO,
                usuario_id=_resolver_usuario(control.ingreso_id, db),
                plazo_objetivo=datetime.combine(control.fecha_control, time.min, tzinfo=timezone.utc),
                ventana_dias=0,
                email_enviado=False,
            )
        )
        creadas += 1
    if creadas:
        db.flush()
        record_audit(db, actor=ACTOR, action="CREATE", entity="alerta_notif", entity_id=f"control:{control.id}")
    return creadas


def resolver_alertas_control(db: Session, control_id: int) -> None:
    """Resuelve las alertas abiertas de un control que el sync va a eliminar."""
    ahora = datetime.now(timezone.utc)
    for alerta in db.scalars(
        select(AlertaNotif).where(
            AlertaNotif.caso_tipo == CASO_TIPO,
            AlertaNotif.caso_id == control_id,
            AlertaNotif.tipo.in_(TIPOS),
            AlertaNotif.estado != EstadoAlerta.RESUELTA.value,
        )
    ):
        alerta.estado = EstadoAlerta.RESUELTA.value
        alerta.resuelta_en = ahora
    db.flush()
