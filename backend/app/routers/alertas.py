"""Router de alertas unificadas (EPIC-10, CEPA-100, CEPA-101, CEPA-102)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.enums_alertas import EstadoAlerta
from app.models.alertas import AlertaNotif
from app.schemas.alertas import AlertaRead, AlertaUpdate, JobResultado
from app.services.alertas import ejecutar_job_alertas

router = APIRouter(prefix="/api/v1/alertas", tags=["alertas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")

# Transiciones de estado válidas (DD-E)
_TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    EstadoAlerta.PENDIENTE.value: {EstadoAlerta.LEIDA.value, EstadoAlerta.RESUELTA.value},
    EstadoAlerta.LEIDA.value: {EstadoAlerta.RESUELTA.value},
    EstadoAlerta.RESUELTA.value: set(),  # estado terminal
}


@router.post(
    "/ejecutar-job",
    response_model=JobResultado,
    dependencies=[Depends(_writer)],
)
def ejecutar_job(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResultado:
    """Ejecuta el job de revisión de plazos perentorios (CEPA-100 RN-2).

    DD-B: la auditoría se registra ANTES del commit dentro del servicio.
    """
    generadas = ejecutar_job_alertas(db, actor=current_user.username)
    return JobResultado(alertas_generadas=generadas, timestamp=datetime.now(timezone.utc))


@router.get("", response_model=list[AlertaRead], dependencies=[Depends(_reader)])
def listar_alertas(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertaNotif]:
    """Panel de notificaciones in-app: devuelve alertas filtradas por rol y asignación.

    - Administrativo: solo sus alertas (usuario_id == current_user.id).
    - Coordinacion/Auditor: todas las alertas (alcance ampliado, RN-2/RN-3 CEPA-101).
    """
    stmt = select(AlertaNotif)
    if current_user.role == "Administrativo":
        stmt = stmt.where(AlertaNotif.usuario_id == current_user.id)
    stmt = stmt.order_by(AlertaNotif.generada_en.desc())
    return list(db.scalars(stmt))


@router.patch("/{alerta_id}", response_model=AlertaRead, dependencies=[Depends(_writer)])
def actualizar_estado_alerta(
    alerta_id: int,
    payload: AlertaUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertaNotif:
    """Marca una alerta como leída o resuelta (CA-4 CEPA-101).

    Valida transiciones (DD-E): pendiente→leida→resuelta (y pendiente→resuelta).
    Rechaza transición desde resuelta (422).
    DD-B: auditoría ANTES del commit.
    """
    alerta = db.get(AlertaNotif, alerta_id)
    if alerta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    estado_actual = alerta.estado
    estado_nuevo = payload.estado.value

    # Validar transición (DD-E)
    permitidos = _TRANSICIONES_VALIDAS.get(estado_actual, set())
    if estado_nuevo not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Transición no permitida: {estado_actual!r} → {estado_nuevo!r}. "
                f"Transiciones válidas desde '{estado_actual}': {sorted(permitidos) or 'ninguna'}."
            ),
        )

    alerta.estado = estado_nuevo
    if payload.estado == EstadoAlerta.RESUELTA:
        alerta.resuelta_en = datetime.now(timezone.utc)
    elif payload.estado != EstadoAlerta.RESUELTA:
        # Al regresar de resuelta (si fuera posible) limpiaríamos resuelta_en;
        # actualmente es terminal pero dejamos el campo intacto intencionalmente.
        pass

    # DD-B: auditoría ANTES del commit
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="alerta_notif",
        entity_id=str(alerta_id),
    )
    db.commit()
    db.refresh(alerta)
    return alerta


@router.post(
    "/enviar-correos",
    response_model=JobResultado,
    dependencies=[Depends(_writer)],
)
def enviar_correos(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResultado:
    """Envía correos de alerta a los responsables (CEPA-102 P1, D12).

    DD-C:
    - Si smtp_host está vacío: retorna inmediatamente con enviados=0 y
      omitidas=N SIN marcar email_enviado (FakeEmailSender nunca se usa
      en la ruta de producción).
    - Las alertas sin usuario o sin email en Usuario.email se cuentan como omitidas.
    No reenvía correos ya enviados (CA-4).
    DD-B: auditoría ANTES del commit dentro del servicio.
    """
    from app.config import get_settings
    from app.services.alertas import enviar_correos_alertas

    settings = get_settings()
    smtp_host = getattr(settings, "smtp_host", "")

    if not smtp_host:
        # Contar alertas pendientes de envío para reportar omitidas (DD-C)
        from sqlalchemy import func
        omitidas = db.scalar(
            select(func.count()).select_from(AlertaNotif).where(
                AlertaNotif.email_enviado == False,  # noqa: E712
                AlertaNotif.estado.in_(["pendiente", "leida"]),
            )
        ) or 0
        return JobResultado(
            alertas_generadas=0,
            omitidas=omitidas,
            timestamp=datetime.now(timezone.utc),
        )

    from app.services.email_sender import SmtpConfig, SmtpEmailSender

    config = SmtpConfig(
        host=smtp_host,
        port=getattr(settings, "smtp_port", 587),
        username=getattr(settings, "smtp_username", ""),
        password=getattr(settings, "smtp_password", ""),
        use_tls=getattr(settings, "smtp_use_tls", True),
        from_addr=getattr(settings, "smtp_from_addr", "cepa-alertas@utalca.cl"),
    )
    sender = SmtpEmailSender(config)

    resultado = enviar_correos_alertas(db, sender=sender, actor=current_user.username)
    return JobResultado(
        alertas_generadas=resultado["enviados"],
        omitidas=resultado["omitidas"],
        timestamp=datetime.now(timezone.utc),
    )
