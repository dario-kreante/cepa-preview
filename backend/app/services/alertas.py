"""Motor de evaluación de plazos perentorios — CEPA-100.

Diseño: función pura `evaluar_plazos()`.
  - Entrada:  lista de HitoPlazos + fecha `hoy` + set de alertas activas.
  - Salida:   lista de ResultadoAlerta a crear (sin efectos secundarios).
  - Sin BD, sin red → completamente testeable como función unitaria.

El job de revisión (`ejecutar_job_alertas`) construye los HitoPlazos
consultando la BD y llama a esta función.

Desviación 1: el modelo ORM se llama AlertaNotif (tabla alerta_notif) para
coexistir con app.models.farmacos.Alerta (tabla alerta, EPIC-02).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Tipos de datos (DTOs del motor — no son modelos ORM)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HitoPlazos:
    """Representa un plazo perentorio a evaluar.

    tipo:              valor de TipoAlerta (str)
    caso_id:           PK del objeto disparador
    caso_tipo:         'ingreso' | 'oda' | 'ept' | 'licencia'
    usuario_id:        PK del usuario Administrativo destinatario
    plazo_objetivo:    date del plazo perentorio
    ventana_dias:      días de anticipación configurados
    usar_dias_habiles: True → cálculo en días hábiles; False → días calendario
    """

    tipo: str
    caso_id: int
    caso_tipo: str
    usuario_id: int
    plazo_objetivo: date
    ventana_dias: int
    usar_dias_habiles: bool = False


@dataclass
class ResultadoAlerta:
    """DTO devuelto por evaluar_plazos; se persistirá como fila en `alerta_notif`."""

    tipo: str
    caso_id: int
    caso_tipo: str
    usuario_id: int
    plazo_objetivo: date
    ventana_dias: int


# ---------------------------------------------------------------------------
# Helper: cálculo de días hábiles
# ---------------------------------------------------------------------------


def dias_habiles_hasta(hoy: date, plazo: date) -> int:
    """Devuelve el número de días hábiles (lun–vie) entre hoy (exclusivo) y plazo (inclusivo).

    Negativo si el plazo ya pasó. No considera festivos.
    """
    if plazo <= hoy:
        delta = 0
        cursor = plazo
        while cursor < hoy:
            if cursor.weekday() < 5:  # 0=lunes … 4=viernes
                delta -= 1
            cursor = cursor + timedelta(days=1)
        return delta

    habiles = 0
    cursor = hoy + timedelta(days=1)
    while cursor <= plazo:
        if cursor.weekday() < 5:
            habiles += 1
        cursor += timedelta(days=1)
    return habiles


# ---------------------------------------------------------------------------
# Motor puro
# ---------------------------------------------------------------------------


def evaluar_plazos(
    hitos: list[HitoPlazos],
    *,
    hoy: date | None = None,
    alertas_activas: set[tuple[int, str]] | None = None,
) -> list[ResultadoAlerta]:
    """Evalúa una lista de hitos y devuelve los que deben generar una nueva alerta.

    Args:
        hitos:           lista de plazos a evaluar.
        hoy:             fecha de referencia (default: date.today()).
        alertas_activas: set de (caso_id, tipo) ya activos — para idempotencia (CA-7).

    Returns:
        Lista de ResultadoAlerta que el llamador persistirá en la BD.
    """
    if hoy is None:
        hoy = date.today()
    if alertas_activas is None:
        alertas_activas = set()

    resultados: list[ResultadoAlerta] = []
    for hito in hitos:
        clave = (hito.caso_id, hito.tipo)
        if clave in alertas_activas:
            continue  # idempotencia: ya existe alerta activa para este (caso, tipo)

        if hito.usar_dias_habiles:
            dias_restantes = dias_habiles_hasta(hoy, hito.plazo_objetivo)
        else:
            dias_restantes = (hito.plazo_objetivo - hoy).days

        if 0 <= dias_restantes <= hito.ventana_dias:
            resultados.append(
                ResultadoAlerta(
                    tipo=hito.tipo,
                    caso_id=hito.caso_id,
                    caso_tipo=hito.caso_tipo,
                    usuario_id=hito.usuario_id,
                    plazo_objetivo=hito.plazo_objetivo,
                    ventana_dias=hito.ventana_dias,
                )
            )
    return resultados


# ---------------------------------------------------------------------------
# Job de revisión: construye hitos desde la BD y persiste alertas
# ---------------------------------------------------------------------------

from app.domain.enums_alertas import EstadoAlerta, TipoAlerta  # noqa: E402
from app.models.alertas import AlertaNotif  # noqa: E402

# Ventanas de aviso por defecto (días). Ajustar según confirmación de Coordinación (RN-3).
VENTANAS_DEFAULT: dict[str, dict] = {
    TipoAlerta.VENCIMIENTO_LICENCIA.value: {"dias": 3, "habiles": True},
    TipoAlerta.PLAZO_EPT.value:            {"dias": 5, "habiles": True},
    TipoAlerta.PLAZO_ISL.value:            {"dias": 5, "habiles": True},
    TipoAlerta.RECETA_POR_RENOVAR.value:   {"dias": 5, "habiles": False},
    TipoAlerta.ODA_POR_VENCER.value:       {"dias": 7, "habiles": False},
    TipoAlerta.CONTROL_MEDICO.value:       {"dias": 7, "habiles": False},
    TipoAlerta.CONSENTIMIENTO_PENDIENTE.value: {"dias": 30, "habiles": False},
}


def _cargar_alertas_activas(db: Session) -> set[tuple[int, str]]:
    """Devuelve el set de (caso_id, tipo) con alertas en estado pendiente o leída."""
    filas = db.execute(
        select(AlertaNotif.caso_id, AlertaNotif.tipo).where(
            AlertaNotif.estado.in_([EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value])
        )
    ).all()
    return {(fila.caso_id, fila.tipo) for fila in filas}


def _construir_hitos_oda(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla oda (EPIC-01).

    Asume columnas: id, fecha_vencimiento, usuario_id.
    Si la columna no existe devuelve lista vacía.
    """
    try:
        filas = db.execute(
            text(
                "SELECT id, fecha_vencimiento, usuario_id FROM oda "
                "WHERE fecha_vencimiento IS NOT NULL"
            )
        ).mappings().all()
    except Exception:
        return []
    ventana = VENTANAS_DEFAULT[TipoAlerta.ODA_POR_VENCER.value]
    hitos = []
    for f in filas:
        if f["fecha_vencimiento"] is None:
            continue
        plazo = f["fecha_vencimiento"]
        if hasattr(plazo, "date"):
            plazo = plazo.date()
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.ODA_POR_VENCER.value,
                caso_id=f["id"],
                caso_tipo="oda",
                usuario_id=f["usuario_id"],
                plazo_objetivo=plazo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_licencias(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla licencia (EPIC-07).

    Asume columnas: id, fecha_fin_reposo, usuario_id.
    """
    try:
        filas = db.execute(
            text(
                "SELECT id, fecha_fin_reposo, usuario_id FROM licencia "
                "WHERE fecha_fin_reposo IS NOT NULL"
            )
        ).mappings().all()
    except Exception:
        return []
    ventana = VENTANAS_DEFAULT[TipoAlerta.VENCIMIENTO_LICENCIA.value]
    hitos = []
    for f in filas:
        if f["fecha_fin_reposo"] is None:
            continue
        plazo = f["fecha_fin_reposo"]
        if hasattr(plazo, "date"):
            plazo = plazo.date()
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.VENCIMIENTO_LICENCIA.value,
                caso_id=f["id"],
                caso_tipo="licencia",
                usuario_id=f["usuario_id"],
                plazo_objetivo=plazo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_ept(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla caso_ept (EPIC-03).

    Asume columnas: id, usuario_id.
    Los plazos vienen de la tabla plazo_ept (fecha_plazo_informe, fecha_plazo_isl).
    Si la tabla no existe devuelve lista vacía.
    """
    hitos: list[HitoPlazos] = []
    try:
        filas = db.execute(
            text(
                "SELECT pe.id AS ept_id, pe.fecha_plazo_informe, "
                "pe.fecha_plazo_isl, ce.usuario_id "
                "FROM plazo_ept pe "
                "JOIN caso_ept ce ON ce.id = pe.caso_ept_id"
            )
        ).mappings().all()
    except Exception:
        return []

    v_ept = VENTANAS_DEFAULT[TipoAlerta.PLAZO_EPT.value]
    v_isl = VENTANAS_DEFAULT[TipoAlerta.PLAZO_ISL.value]
    for f in filas:
        for campo, tipo, ventana in [
            ("fecha_plazo_informe", TipoAlerta.PLAZO_EPT.value, v_ept),
            ("fecha_plazo_isl", TipoAlerta.PLAZO_ISL.value, v_isl),
        ]:
            if f[campo] is None:
                continue
            plazo = f[campo]
            if hasattr(plazo, "date"):
                plazo = plazo.date()
            hitos.append(
                HitoPlazos(
                    tipo=tipo,
                    caso_id=f["ept_id"],
                    caso_tipo="ept",
                    usuario_id=f["usuario_id"],
                    plazo_objetivo=plazo,
                    ventana_dias=ventana["dias"],
                    usar_dias_habiles=ventana["habiles"],
                )
            )
    return hitos


def _construir_hitos_consentimiento(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos para ingresos sin consentimiento firmado.

    Usa la tabla consentimiento (EPIC-01). Un ingreso sin consentimiento aceptado
    genera alerta permanente hasta que se firme.
    """
    try:
        # Ingresos que NO tienen consentimiento aceptado
        filas = db.execute(
            text(
                "SELECT i.id, i.usuario_id, i.fecha_ingreso "
                "FROM ingreso i "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM consentimiento c "
                "  WHERE c.ingreso_id = i.id AND c.estado = 'aceptado'"
                ")"
            )
        ).mappings().all()
    except Exception:
        return []

    ventana = VENTANAS_DEFAULT[TipoAlerta.CONSENTIMIENTO_PENDIENTE.value]
    hitos = []
    for f in filas:
        plazo = f.get("fecha_ingreso") or date.today()
        if hasattr(plazo, "date"):
            plazo = plazo.date()
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.CONSENTIMIENTO_PENDIENTE.value,
                caso_id=f["id"],
                caso_tipo="ingreso",
                usuario_id=f["usuario_id"],
                plazo_objetivo=plazo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def ejecutar_job_alertas(db: Session, *, actor: str = "sistema") -> int:
    """Job principal de revisión de plazos.

    Construye todos los hitos de dominio, evalúa plazos y persiste las alertas nuevas.
    Devuelve el número de alertas generadas en esta ejecución.
    Registra auditoría vía record_audit (RN-8, CA-8).
    """
    from app.audit.service import record_audit

    hoy = date.today()

    hitos: list[HitoPlazos] = []
    hitos.extend(_construir_hitos_oda(db))
    hitos.extend(_construir_hitos_licencias(db))
    hitos.extend(_construir_hitos_ept(db))
    hitos.extend(_construir_hitos_consentimiento(db))

    alertas_activas = _cargar_alertas_activas(db)
    resultados = evaluar_plazos(hitos, hoy=hoy, alertas_activas=alertas_activas)

    for r in resultados:
        alerta = AlertaNotif(
            tipo=r.tipo,
            estado=EstadoAlerta.PENDIENTE.value,
            caso_id=r.caso_id,
            caso_tipo=r.caso_tipo,
            usuario_id=r.usuario_id,
            plazo_objetivo=datetime.combine(
                r.plazo_objetivo, datetime.min.time()
            ).replace(tzinfo=timezone.utc),
            ventana_dias=r.ventana_dias,
            email_enviado=False,
        )
        db.add(alerta)

    if resultados:
        db.commit()
        record_audit(
            db,
            actor=actor,
            action="CREATE",
            entity="alerta_notif",
            entity_id=f"job:{len(resultados)}",
        )

    return len(resultados)


def enviar_correos_alertas(
    db: Session,
    *,
    sender,
    actor: str = "sistema",
) -> int:
    """Recorre las alertas pendientes de envío y envía correo a cada destinatario.

    Filtra email_enviado=False para evitar duplicados (CA-4, TC-102-04).
    Actualiza email_enviado=True solo si el envío fue exitoso.
    Devuelve el número de correos enviados en esta ejecución.
    """
    from app.audit.service import record_audit
    from app.services.email_sender import enviar_alerta

    alertas_pendientes = db.scalars(
        select(AlertaNotif).where(
            AlertaNotif.email_enviado == False,  # noqa: E712
            AlertaNotif.estado.in_(["pendiente", "leida"]),
        )
    ).all()

    enviados = 0
    for alerta in alertas_pendientes:
        # Obtener correo del usuario desde la tabla de usuarios
        try:
            fila = db.execute(
                text("SELECT email FROM usuario WHERE id = :uid"),
                {"uid": alerta.usuario_id},
            ).mappings().first()
            correo = fila["email"] if fila and fila.get("email") else None
        except Exception:
            correo = None

        plazo_str = str(
            alerta.plazo_objetivo.date()
            if hasattr(alerta.plazo_objetivo, "date")
            else alerta.plazo_objetivo
        )
        ok = enviar_alerta(
            sender=sender,
            to_email=correo,
            tipo_alerta=alerta.tipo,
            caso_tipo=alerta.caso_tipo,
            caso_id=alerta.caso_id,
            plazo_str=plazo_str,
        )
        if ok:
            alerta.email_enviado = True
            enviados += 1

    if enviados:
        db.commit()
        record_audit(
            db,
            actor=actor,
            action="UPDATE",
            entity="alerta_notif",
            entity_id=f"email:{enviados}",
        )

    return enviados
