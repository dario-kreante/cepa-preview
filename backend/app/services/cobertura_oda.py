"""Cobertura de la ODA: qué ODA del ingreso cubre una fecha de atención (reunión 29-10, D9).

La ODA/OPA del ISL autoriza atender al paciente entre su inicio de vigencia
(``fecha_registro``, que la carga del reporte ISL llena con «Inicio Vigencia») y su
``fecha_vencimiento``. Un control o una cita fuera de toda ODA del ingreso no está
cubierto: el CEPA tiene que pedir la ODA o su renovación antes de atender o facturar.

Solo se evalúa en ingresos que tienen al menos una ODA registrada: sin ODA cargada no
se sabe nada (y la alerta «ODA por vencer» no aplica).
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums import EstadoCaso
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import AlertaNotif
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.oda import Oda

CASO_TIPO_CITA = "salutem_cita"
# Citas ya realizadas que se revisan hacia atrás (facturación de la semana).
DIAS_ATRAS = 7
_ABIERTAS = (EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value)


def oda_que_cubre(odas: Iterable[Oda], fecha: date) -> Oda | None:
    """La ODA que cubre la fecha (la que vence más tarde si hay varias)."""
    cubren = [
        o for o in odas
        if (o.fecha_registro is None or o.fecha_registro <= fecha) and fecha <= o.fecha_vencimiento
    ]
    return max(cubren, key=lambda o: (o.fecha_vencimiento, o.id), default=None)


def odas_por_ingreso(db: Session, ingreso_ids: set[int]) -> dict[int, list[Oda]]:
    resultado: dict[int, list[Oda]] = defaultdict(list)
    if ingreso_ids:
        for oda in db.scalars(select(Oda).where(Oda.ingreso_id.in_(ingreso_ids))):
            resultado[oda.ingreso_id].append(oda)
    return resultado


def alertar_citas_fuera_de_oda(
    db: Session, hoy: date, ventanas: dict, actor: str
) -> tuple[int, int]:
    """Crea las alertas de citas sin ODA que las cubra y resuelve las que ya quedaron cubiertas.

    Una alerta por cita para siempre (si se resolvió a mano no reaparece). Devuelve
    (creadas, resueltas).
    """
    from app.services.alertas import _resolver_usuario

    ventana = ventanas.get(TipoAlerta.CITA_FUERA_DE_ODA.value, {"dias": 30})
    resueltas = resolver_citas_cubiertas(db, actor)
    if not ventana.get("activo", True):
        return 0, resueltas

    desde, hasta = hoy - timedelta(days=DIAS_ATRAS), hoy + timedelta(days=int(ventana.get("dias", 30)))
    citas = list(
        db.scalars(
            select(Cita)
            .join(Ingreso, Ingreso.id == Cita.ingreso_id)
            .where(
                Cita.salutem_cita_id.is_not(None),
                Cita.estado.in_(("agendada", "realizada")),
                Cita.fecha >= desde,
                Cita.fecha <= hasta,
                Ingreso.estado == EstadoCaso.ACTIVO.value,
            )
        )
    )
    odas = odas_por_ingreso(db, {c.ingreso_id for c in citas})
    ya_alertadas = set(
        db.scalars(
            select(AlertaNotif.caso_id).where(
                AlertaNotif.tipo == TipoAlerta.CITA_FUERA_DE_ODA.value,
                AlertaNotif.caso_tipo == CASO_TIPO_CITA,
            )
        )
    )
    creadas = 0
    for cita in citas:
        if not odas.get(cita.ingreso_id) or cita.salutem_cita_id in ya_alertadas:
            continue
        if oda_que_cubre(odas[cita.ingreso_id], cita.fecha) is not None:
            continue
        db.add(
            AlertaNotif(
                tipo=TipoAlerta.CITA_FUERA_DE_ODA.value,
                estado=EstadoAlerta.PENDIENTE.value,
                caso_id=cita.salutem_cita_id,
                caso_tipo=CASO_TIPO_CITA,
                usuario_id=_resolver_usuario(cita.ingreso_id, db),
                plazo_objetivo=datetime.combine(cita.fecha, time.min, tzinfo=timezone.utc),
                ventana_dias=int(ventana.get("dias", 30)),
                email_enviado=False,
            )
        )
        ya_alertadas.add(cita.salutem_cita_id)
        creadas += 1
    if creadas:
        db.flush()
        record_audit(
            db, actor=actor, action="CREATE", entity="alerta_notif",
            entity_id=f"fuera-de-oda:{creadas}",
        )
    return creadas, resueltas


def resolver_citas_cubiertas(db: Session, actor: str) -> int:
    """Resuelve las alertas abiertas cuya cita ya cubre una ODA (p. ej. tras cargar el reporte ISL)."""
    filas = db.execute(
        select(AlertaNotif, Cita)
        .join(Cita, Cita.salutem_cita_id == AlertaNotif.caso_id)
        .where(
            AlertaNotif.tipo == TipoAlerta.CITA_FUERA_DE_ODA.value,
            AlertaNotif.caso_tipo == CASO_TIPO_CITA,
            AlertaNotif.estado.in_(_ABIERTAS),
        )
    ).all()
    if not filas:
        return 0
    odas = odas_por_ingreso(db, {c.ingreso_id for _, c in filas})
    ahora = datetime.now(timezone.utc)
    resueltas = 0
    for alerta, cita in filas:
        if oda_que_cubre(odas.get(cita.ingreso_id, []), cita.fecha) is not None:
            alerta.estado = EstadoAlerta.RESUELTA.value
            alerta.resuelta_en = ahora
            resueltas += 1
    if resueltas:
        db.flush()
        record_audit(
            db, actor=actor, action="UPDATE", entity="alerta_notif",
            entity_id=f"oda-cubre:{resueltas}", valor_nuevo=EstadoAlerta.RESUELTA.value,
        )
    return resueltas
