from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    entity: str,
    entity_id: str | None = None,
    rol: str | None = None,
    valor_anterior: str | None = None,
    valor_nuevo: str | None = None,
) -> AuditLog:
    """Registra una traza append-only de auditoría (CEPA-003).

    `action` ∈ {CREATE, UPDATE, DELETE, LOGIN, LOGIN_FALLIDO, BLOQUEO}.
    NO hace commit: la traza se confirma o se revierte junto con la transacción del caller,
    evitando trazas parciales (TC-003-05).
    """
    traza = AuditLog(
        actor=actor,
        rol=rol,
        action=action,
        entity=entity,
        entity_id=entity_id,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
    )
    db.add(traza)
    return traza
