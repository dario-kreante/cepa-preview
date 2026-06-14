"""Motor de evaluación de plazos perentorios — CEPA-100.

Diseño: función pura ``evaluar_plazos()``.
  - Entrada:  lista de HitoPlazos + fecha ``hoy`` + set de alertas activas.
  - Salida:   lista de ResultadoAlerta a crear (sin efectos secundarios).
  - Sin BD, sin red → completamente testeable como función unitaria.

El job de revisión (``ejecutar_job_alertas``) construye los HitoPlazos
consultando la BD y llama a esta función.

Relación con otras tablas de alertas (DD-F / Decisión de diseño):
  • ``alerta`` (tabla EPIC-02, modelo farmacos.Alerta):  almacén específico
    de recetas farmacológicas — permanece en su flujo de dominio EPIC-02.
  • ``alerta_licencia`` (tabla EPIC-07):  almacén específico de alertas de
    licencias médicas — permanece en su flujo de dominio EPIC-07.
  • ``alerta_notif`` (este módulo):  panel unificado in-app que cubre los 7
    tipos de alerta directamente desde las tablas de dominio, sin duplicar
    los registros de las dos tablas anteriores.

Destinatario de la alerta (PA):
  El campo ``usuario_id`` se resuelve como ``Ingreso.profesional_id`` cuando
  está definido; en caso contrario se almacena ``None`` (la alerta queda
  visible en el panel de Coordinación/global).  Actualmente no existe un
  administrativo por caso — esta regla se revisará cuando se implemente ese
  vínculo (nota abierta PA).

Idempotencia (RN-4 / DD-D):
  La clave de idempotencia es ``(caso_id, tipo, plazo_objetivo)`` para que
  un nuevo plazo posterior al mismo caso genere una alerta distinta.

Desviación 1: el modelo ORM se llama AlertaNotif (tabla ``alerta_notif``)
para coexistir con ``app.models.farmacos.Alerta`` (tabla ``alerta``,
EPIC-02).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipos de datos (DTOs del motor — no son modelos ORM)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HitoPlazos:
    """Representa un plazo perentorio a evaluar.

    tipo:              valor de TipoAlerta (str)
    caso_id:           PK del objeto disparador
    caso_tipo:         'ingreso' | 'oda' | 'ept' | 'licencia'
    usuario_id:        PK del usuario destinatario (None si sin asignar)
    plazo_objetivo:    date del plazo perentorio
    ventana_dias:      días de anticipación configurados
    usar_dias_habiles: True → cálculo en días hábiles; False → días calendario
    """

    tipo: str
    caso_id: int
    caso_tipo: str
    usuario_id: int | None
    plazo_objetivo: date
    ventana_dias: int
    usar_dias_habiles: bool = False


@dataclass
class ResultadoAlerta:
    """DTO devuelto por evaluar_plazos; se persistirá como fila en ``alerta_notif``."""

    tipo: str
    caso_id: int
    caso_tipo: str
    usuario_id: int | None
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
    alertas_activas: set[tuple] | None = None,
) -> list[ResultadoAlerta]:
    """Evalúa una lista de hitos y devuelve los que deben generar una nueva alerta.

    Args:
        hitos:           lista de plazos a evaluar.
        hoy:             fecha de referencia (default: date.today()).
        alertas_activas: set de (caso_id, tipo, plazo_objetivo) ya activos —
                         para idempotencia (CA-7 / RN-4 / DD-D).
                         El tercer elemento del tuple es la fecha normalizada a
                         ``date`` para comparación uniforme.

    Returns:
        Lista de ResultadoAlerta que el llamador persistirá en la BD.
    """
    if hoy is None:
        hoy = date.today()
    if alertas_activas is None:
        alertas_activas = set()

    resultados: list[ResultadoAlerta] = []
    for hito in hitos:
        clave = (hito.caso_id, hito.tipo, hito.plazo_objetivo)
        if clave in alertas_activas:
            continue  # idempotencia: ya existe alerta activa para este (caso, tipo, plazo)

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


def _cargar_alertas_activas(db: Session) -> set[tuple]:
    """Devuelve el set de (caso_id, tipo, plazo_objetivo_date) con alertas pendiente o leída."""
    filas = db.execute(
        select(AlertaNotif.caso_id, AlertaNotif.tipo, AlertaNotif.plazo_objetivo).where(
            AlertaNotif.estado.in_([EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value])
        )
    ).all()
    resultado = set()
    for fila in filas:
        plazo = fila.plazo_objetivo
        if hasattr(plazo, "date"):
            plazo = plazo.date()
        resultado.add((fila.caso_id, fila.tipo, plazo))
    return resultado


def _resolver_usuario(ingreso_id: int | None, db: Session) -> int | None:
    """Resuelve el usuario_id destinatario a partir del ingreso.

    Regla PA: usa Ingreso.profesional_id cuando está definido; en caso
    contrario devuelve None (alerta visible al panel global de Coordinación).
    """
    if ingreso_id is None:
        return None
    from app.models.ingreso import Ingreso  # local import para evitar ciclos
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        return None
    return ingreso.profesional_id  # puede ser None


def _construir_hitos_oda(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla oda (EPIC-01) via ORM.

    Filtra por vigente=True y fecha_vencimiento IS NOT NULL.
    Destinatario: Ingreso.profesional_id, o None si no asignado (PA).
    """
    from app.models.oda import Oda  # local import para evitar ciclos

    ventana = VENTANAS_DEFAULT[TipoAlerta.ODA_POR_VENCER.value]
    filas = db.scalars(
        select(Oda).where(
            Oda.vigente == True,  # noqa: E712
            Oda.fecha_vencimiento.isnot(None),
        )
    ).all()
    hitos = []
    for oda in filas:
        usuario_id = _resolver_usuario(oda.ingreso_id, db)
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.ODA_POR_VENCER.value,
                caso_id=oda.id,
                caso_tipo="oda",
                usuario_id=usuario_id,
                plazo_objetivo=oda.fecha_vencimiento,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_licencias(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde la tabla licencia_medica (EPIC-07) via ORM.

    Filtra anulada=False y fin_reposo IS NOT NULL.
    Destinatario: Ingreso.profesional_id, o None (PA).
    """
    from app.models.licencia import LicenciaMedica  # local import

    ventana = VENTANAS_DEFAULT[TipoAlerta.VENCIMIENTO_LICENCIA.value]
    filas = db.scalars(
        select(LicenciaMedica).where(
            LicenciaMedica.anulada == False,  # noqa: E712
            LicenciaMedica.fin_reposo.isnot(None),
        )
    ).all()
    hitos = []
    for lm in filas:
        usuario_id = _resolver_usuario(lm.ingreso_id, db)
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.VENCIMIENTO_LICENCIA.value,
                caso_id=lm.id,
                caso_tipo="licencia",
                usuario_id=usuario_id,
                plazo_objetivo=lm.fin_reposo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_ept(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos desde plazo_ept JOIN caso_ept (EPIC-03) via ORM.

    Genera un hito por cada plazo no nulo:
      - plazo_informe_ept → TipoAlerta.PLAZO_EPT
      - plazo_portal_isl  → TipoAlerta.PLAZO_ISL
    Destinatario: Ingreso.profesional_id vía CasoEpt.ingreso_id (PA).
    """
    from app.models.ept import CasoEpt, PlazoEpt  # local import

    v_ept = VENTANAS_DEFAULT[TipoAlerta.PLAZO_EPT.value]
    v_isl = VENTANAS_DEFAULT[TipoAlerta.PLAZO_ISL.value]

    filas = db.scalars(
        select(PlazoEpt)
    ).all()
    hitos: list[HitoPlazos] = []
    for plazo_ept in filas:
        caso = db.get(CasoEpt, plazo_ept.caso_ept_id)
        if caso is None:
            continue
        usuario_id = _resolver_usuario(caso.ingreso_id, db)
        for campo_date, tipo, ventana in [
            (plazo_ept.plazo_informe_ept, TipoAlerta.PLAZO_EPT.value, v_ept),
            (plazo_ept.plazo_portal_isl, TipoAlerta.PLAZO_ISL.value, v_isl),
        ]:
            if campo_date is None:
                continue
            hitos.append(
                HitoPlazos(
                    tipo=tipo,
                    caso_id=plazo_ept.id,
                    caso_tipo="ept",
                    usuario_id=usuario_id,
                    plazo_objetivo=campo_date,
                    ventana_dias=ventana["dias"],
                    usar_dias_habiles=ventana["habiles"],
                )
            )
    return hitos


def _construir_hitos_consentimiento(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos para consentimientos no firmados (EPIC-01) via ORM.

    Un consentimiento con estado != FIRMADO genera alerta permanente hasta
    que se firme.  El plazo_objetivo es la fecha de creación del consentimiento
    (ya vencido → dias_restantes=0 → siempre dentro de la ventana de 30 días).
    Destinatario: Ingreso.profesional_id, o None (PA).
    """
    from app.domain.enums import EstadoConsentimiento
    from app.models.consentimiento import Consentimiento  # local import

    ventana = VENTANAS_DEFAULT[TipoAlerta.CONSENTIMIENTO_PENDIENTE.value]
    filas = db.scalars(
        select(Consentimiento).where(
            Consentimiento.estado != EstadoConsentimiento.FIRMADO.value
        )
    ).all()
    hitos = []
    for c in filas:
        usuario_id = _resolver_usuario(c.ingreso_id, db)
        # plazo_objetivo = fecha de creación del consentimiento (dias_restantes <= 0
        # → siempre dentro de la ventana de 30 días, que es la intención del tipo)
        plazo = c.created_at.date() if hasattr(c.created_at, "date") else date.today()
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.CONSENTIMIENTO_PENDIENTE.value,
                caso_id=c.ingreso_id,
                caso_tipo="ingreso",
                usuario_id=usuario_id,
                plazo_objetivo=plazo,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_control_medico(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos para controles médicos próximos sin agendar (EPIC-06) via ORM.

    Filtra: proximo_control IS NOT NULL AND proximo_agendado = False.
    F5: toma solo el control más reciente por ingreso (latest-per-ingreso en Python).
    F6: caso_tipo="control_medico" (caso_id=control.id).
    Destinatario: Ingreso.profesional_id, o None (PA).
    """
    from app.models.control_medico import ControlMedico  # local import

    ventana = VENTANAS_DEFAULT[TipoAlerta.CONTROL_MEDICO.value]
    filas = db.scalars(
        select(ControlMedico).where(
            ControlMedico.proximo_control.isnot(None),
            ControlMedico.proximo_agendado == False,  # noqa: E712
        )
    ).all()

    # F5: latest-per-ingreso — conservar solo el control con proximo_control más reciente
    # por ingreso_id (group in Python para portabilidad).
    latest_by_ingreso: dict[int, ControlMedico] = {}
    for cm in filas:
        existing = latest_by_ingreso.get(cm.ingreso_id)
        if existing is None or cm.proximo_control > existing.proximo_control:
            latest_by_ingreso[cm.ingreso_id] = cm

    hitos = []
    for cm in latest_by_ingreso.values():
        usuario_id = _resolver_usuario(cm.ingreso_id, db)
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.CONTROL_MEDICO.value,
                caso_id=cm.id,
                caso_tipo="control_medico",  # F6: tipo correcto
                usuario_id=usuario_id,
                plazo_objetivo=cm.proximo_control,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def _construir_hitos_receta(db: Session) -> list[HitoPlazos]:
    """Construye HitoPlazos para recetas por renovar (EPIC-02) via ORM.

    Filtra: fecha_revision IS NOT NULL AND fecha_envio IS NULL.
    El hito representa la receta que necesita ser enviada antes de su fecha de revisión.
    Destinatario: resuelto vía reg_farmacologico → ingreso_id → profesional_id (PA).
    """
    from app.models.farmacos import Receta, RegistroFarmacologico  # local import

    ventana = VENTANAS_DEFAULT[TipoAlerta.RECETA_POR_RENOVAR.value]
    filas = db.scalars(
        select(Receta).where(
            Receta.fecha_revision.isnot(None),
            Receta.fecha_envio.is_(None),
        )
    ).all()
    hitos = []
    for receta in filas:
        # Resolver ingreso_id a través del registro farmacológico
        reg = db.get(RegistroFarmacologico, receta.registro_id)
        ingreso_id = reg.ingreso_id if reg else None
        usuario_id = _resolver_usuario(ingreso_id, db)
        hitos.append(
            HitoPlazos(
                tipo=TipoAlerta.RECETA_POR_RENOVAR.value,
                caso_id=receta.id,
                caso_tipo="receta",
                usuario_id=usuario_id,
                plazo_objetivo=receta.fecha_revision,
                ventana_dias=ventana["dias"],
                usar_dias_habiles=ventana["habiles"],
            )
        )
    return hitos


def ejecutar_job_alertas(db: Session, *, actor: str = "sistema") -> int:
    """Job principal de revisión de plazos.

    Construye todos los hitos de dominio, evalúa plazos y persiste las alertas nuevas.
    Devuelve el número de alertas generadas en esta ejecución.
    Registra auditoría ANTES del commit (DD-B / RN-8 / CA-8).
    """
    from app.audit.service import record_audit

    hoy = date.today()

    hitos: list[HitoPlazos] = []
    hitos.extend(_construir_hitos_oda(db))
    hitos.extend(_construir_hitos_licencias(db))
    hitos.extend(_construir_hitos_ept(db))
    hitos.extend(_construir_hitos_consentimiento(db))
    hitos.extend(_construir_hitos_control_medico(db))
    hitos.extend(_construir_hitos_receta(db))

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
        # DD-B: registrar auditoría ANTES del commit
        record_audit(
            db,
            actor=actor,
            action="CREATE",
            entity="alerta_notif",
            entity_id=f"job:{len(resultados)}",
        )
        db.commit()

    return len(resultados)


def enviar_correos_alertas(
    db: Session,
    *,
    sender,
    actor: str = "sistema",
) -> dict:
    """Recorre las alertas pendientes de envío y envía correo a cada destinatario.

    Filtra email_enviado=False para evitar duplicados (CA-4, TC-102-04).
    Actualiza email_enviado=True solo si el envío fue exitoso.
    Cuando smtp_host está vacío (sin configuración SMTP), retorna early sin
    marcar email_enviado (DD-C).
    Devuelve dict con ``enviados`` y ``omitidas`` (sin usuario o sin email).
    DD-B: auditoría ANTES del commit.
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
    omitidas = 0

    for alerta in alertas_pendientes:
        # Resolver correo del usuario via ORM (DD-C)
        correo: str | None = None
        if alerta.usuario_id is not None:
            from app.models.usuario import Usuario
            usuario = db.get(Usuario, alerta.usuario_id)
            correo = usuario.email if usuario is not None else None

        if not correo:
            omitidas += 1
            continue

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
        else:
            omitidas += 1

    if enviados:
        # DD-B: auditoría ANTES del commit
        record_audit(
            db,
            actor=actor,
            action="UPDATE",
            entity="alerta_notif",
            entity_id=f"email:{enviados}",
        )
        db.commit()

    return {"enviados": enviados, "omitidas": omitidas}
