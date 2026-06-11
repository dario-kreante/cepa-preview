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


@router.post(
    "/ejecutar-job",
    response_model=JobResultado,
    dependencies=[Depends(_writer)],
)
def ejecutar_job(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResultado:
    """Ejecuta el job de revisión de plazos perentorios (CEPA-100 RN-2)."""
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
    """Marca una alerta como leída o resuelta (CA-4 CEPA-101)."""
    alerta = db.get(AlertaNotif, alerta_id)
    if alerta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    alerta.estado = payload.estado.value
    if payload.estado == EstadoAlerta.RESUELTA:
        alerta.resuelta_en = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alerta)
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="alerta_notif",
        entity_id=str(alerta_id),
    )
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

    Degradación controlada si SMTP no está disponible (CA-3).
    No reenvía correos ya enviados (CA-4).
    """
    from app.services.alertas import enviar_correos_alertas
    from app.services.email_sender import FakeEmailSender

    # En producción, construir el sender desde config SMTP.
    # Aquí se usa FakeEmailSender si SMTP_HOST no está configurado (degradación controlada).
    from app.config import get_settings
    settings = get_settings()
    smtp_host = getattr(settings, "smtp_host", "")
    if smtp_host:
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
    else:
        sender = FakeEmailSender()

    enviados = enviar_correos_alertas(db, sender=sender, actor=current_user.username)
    return JobResultado(alertas_generadas=enviados, timestamp=datetime.now(timezone.utc))
