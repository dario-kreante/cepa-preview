"""Alerta «Pendiente de remitir a ISL» (QA-010, 23-11-2026).

Un caso de reintegro activo de un paciente ISL que lleva ``dias`` días corridos (por defecto 7;
se edita en la configuración de alertas) desde su ``fecha_caso`` sin marcarse «Remitido a ISL»
avisa que falta remitirlo.

- Activo = estado de reintegro distinto de «total» e ingreso no cerrado.
- Paciente ISL: ver ``reintegro_isl``.
- Solo casos de hasta ``ANTIGUEDAD_MAXIMA_DIAS`` (60) días desde su fecha, como «RECA por
  solicitar»: al desplegar, los casos históricos (que hasta ahora solo se marcaban remitidos al
  cerrar) no llenan el panel.
- Una alerta por caso para siempre: si la encargada la resuelve a mano no reaparece.
- Se resuelve sola al marcar el caso remitido (`resolver_alertas_remitir_isl`, desde el servicio
  del caso) y, en el job, al pasar a reintegro total o al cerrarse el ingreso.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums import EstadoCaso
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.domain.reintegro_enums import EstadoReintegro
from app.models.alertas import AlertaNotif
from app.models.ingreso import Ingreso
from app.models.reintegro import CasoReintegro
from app.services.alertas_reca import ANTIGUEDAD_MAXIMA_DIAS, CASO_TIPO
from app.services.reintegro_isl import ingreso_es_isl

TIPO = TipoAlerta.PENDIENTE_REMITIR_ISL.value
_ABIERTAS = (EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value)


def _no_requiere_remision():
    """El caso ya no necesita remitirse: se remitió, terminó o se cerró su ingreso."""
    return or_(
        CasoReintegro.remitido_isl == true(),
        CasoReintegro.estado_reintegro == EstadoReintegro.TOTAL.value,
        Ingreso.estado == EstadoCaso.CERRADO.value,
    )


def resolver_alertas_remitir_isl(db: Session, caso_id: int) -> int:
    """Resuelve las alertas abiertas «Pendiente de remitir a ISL» de un caso. Devuelve cuántas."""
    ahora = datetime.now(timezone.utc)
    alertas = db.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == TIPO,
            AlertaNotif.caso_tipo == CASO_TIPO,
            AlertaNotif.caso_id == caso_id,
            AlertaNotif.estado.in_(_ABIERTAS),
        )
    ).all()
    for alerta in alertas:
        alerta.estado = EstadoAlerta.RESUELTA.value
        alerta.resuelta_en = ahora
    if alertas:
        db.flush()
    return len(alertas)


def alertar_pendiente_remitir_isl(
    db: Session, hoy: date, ventanas: dict, actor: str
) -> tuple[int, int]:
    """Crea las alertas que faltan y resuelve las que dejaron de aplicar. Devuelve (creadas, resueltas)."""
    config = ventanas.get(TIPO, {})
    ahora = datetime.now(timezone.utc)

    resueltas = 0
    obsoletas = db.scalars(
        select(AlertaNotif)
        .join(CasoReintegro, CasoReintegro.id == AlertaNotif.caso_id)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(
            AlertaNotif.tipo == TIPO,
            AlertaNotif.caso_tipo == CASO_TIPO,
            AlertaNotif.estado.in_(_ABIERTAS),
            _no_requiere_remision(),
        )
    ).all()
    for alerta in obsoletas:
        alerta.estado = EstadoAlerta.RESUELTA.value
        alerta.resuelta_en = ahora
        resueltas += 1
    if resueltas:
        db.flush()
        record_audit(
            db, actor=actor, action="UPDATE", entity="alerta_notif",
            entity_id=f"remitir-isl-resuelta:{resueltas}", valor_nuevo=EstadoAlerta.RESUELTA.value,
        )

    if not config.get("activo", True):
        return 0, resueltas
    dias = config.get("dias", 7)

    ya_alertados = set(
        db.scalars(select(AlertaNotif.caso_id).where(AlertaNotif.tipo == TIPO, AlertaNotif.caso_tipo == CASO_TIPO))
    )
    from app.services.alertas import _resolver_usuario  # noqa: PLC0415 (evita ciclo de importación)

    candidatos = db.execute(
        select(CasoReintegro.id, CasoReintegro.fecha_caso, CasoReintegro.ingreso_id)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(
            CasoReintegro.fecha_caso <= hoy - timedelta(days=dias),
            CasoReintegro.fecha_caso >= hoy - timedelta(days=ANTIGUEDAD_MAXIMA_DIAS),
            ~_no_requiere_remision(),
            ingreso_es_isl(),
        )
        .order_by(CasoReintegro.id)
    ).all()
    creadas = 0
    for caso_id, fecha_caso, ingreso_id in candidatos:
        if caso_id in ya_alertados:
            continue
        plazo = fecha_caso + timedelta(days=dias)
        db.add(
            AlertaNotif(
                tipo=TIPO,
                estado=EstadoAlerta.PENDIENTE.value,
                caso_id=caso_id,
                caso_tipo=CASO_TIPO,
                usuario_id=_resolver_usuario(ingreso_id, db),
                plazo_objetivo=datetime.combine(plazo, time.min, tzinfo=timezone.utc),
                ventana_dias=dias,
                email_enviado=False,
            )
        )
        creadas += 1
    if creadas:
        db.flush()
        record_audit(
            db, actor=actor, action="CREATE", entity="alerta_notif", entity_id=f"remitir-isl:{creadas}"
        )
    return creadas, resueltas
