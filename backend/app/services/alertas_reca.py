"""Alerta «RECA por solicitar» (QA-003, 18-11-2026).

Un caso de reintegro activo que lleva ``dias`` días corridos (por defecto 5, PROVISIONAL: la
clienta debe confirmarlo; se edita en la configuración de alertas) desde su ``fecha_caso`` sin
fecha de solicitud de RECA ni RECA registrada avisa que hay que pedirla.

- Activo = estado de reintegro distinto de «total» e ingreso no cerrado.
- Solo casos de hasta ``ANTIGUEDAD_MAXIMA_DIAS`` (60) días desde su fecha: los más antiguos no
  generan alerta (las ya abiertas no se tocan).
- Una alerta por caso para siempre: si la encargada la resuelve a mano no reaparece.
- Se resuelve sola al registrar la solicitud o la RECA (`resolver_alertas_reca`, desde los
  servicios del caso) y, en el job, al pasar a reintegro total o al cerrarse el ingreso.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums import EstadoCaso
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.domain.reintegro_enums import EstadoReintegro
from app.models.alertas import AlertaNotif
from app.models.ingreso import Ingreso
from app.models.reintegro import CasoReintegro, Reca

CASO_TIPO = "caso_reintegro"
# Corte de antigüedad: un caso con más de estos días corridos desde su fecha no genera la alerta.
# Evita que, al desplegar, el panel se llene con casos históricos sin solicitud ni RECA.
ANTIGUEDAD_MAXIMA_DIAS = 60
TIPO = TipoAlerta.RECA_POR_SOLICITAR.value
_ABIERTAS = (EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value)


def _con_reca():
    return exists().where(Reca.caso_reintegro_id == CasoReintegro.id)


def _no_requiere_solicitud():
    """El caso ya no necesita solicitar la RECA: la pidió, la recibió, terminó o se cerró."""
    return or_(
        CasoReintegro.fecha_solicitud_reca.is_not(None),
        _con_reca(),
        CasoReintegro.estado_reintegro == EstadoReintegro.TOTAL.value,
        Ingreso.estado == EstadoCaso.CERRADO.value,
    )


def resolver_alertas_reca(db: Session, caso_id: int) -> int:
    """Resuelve las alertas abiertas «RECA por solicitar» de un caso. Devuelve cuántas."""
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


def alertar_reca_por_solicitar(
    db: Session, hoy: date, ventanas: dict, actor: str
) -> tuple[int, int]:
    """Crea las alertas que faltan y resuelve las que dejaron de aplicar. Devuelve (creadas, resueltas)."""
    config = ventanas.get(TIPO, {})
    ahora = datetime.now(timezone.utc)

    # Resolución: casos con una alerta abierta que ya no requieren solicitar la RECA.
    resueltas = 0
    obsoletas = db.scalars(
        select(AlertaNotif)
        .join(CasoReintegro, CasoReintegro.id == AlertaNotif.caso_id)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(
            AlertaNotif.tipo == TIPO,
            AlertaNotif.caso_tipo == CASO_TIPO,
            AlertaNotif.estado.in_(_ABIERTAS),
            _no_requiere_solicitud(),
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
            entity_id=f"reca-resuelta:{resueltas}", valor_nuevo=EstadoAlerta.RESUELTA.value,
        )

    if not config.get("activo", True):
        return 0, resueltas
    dias = config.get("dias", 5)

    # Creación: casos activos sin solicitud ni RECA, a `dias` días corridos o más de su fecha.
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
            ~_no_requiere_solicitud(),
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
            db, actor=actor, action="CREATE", entity="alerta_notif", entity_id=f"reca:{creadas}"
        )
    return creadas, resueltas
