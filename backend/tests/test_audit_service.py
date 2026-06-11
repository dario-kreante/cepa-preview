from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.audit_log import AuditLog


def test_record_audit_crea_una_traza(db_session: Session):
    record_audit(
        db_session,
        actor="maria",
        action="CREATE",
        entity="usuario",
        entity_id="42",
        rol="Coordinacion",
    )
    db_session.flush()
    traza = db_session.scalars(select(AuditLog).where(AuditLog.entity_id == "42")).one()
    assert traza.actor == "maria"
    assert traza.action == "CREATE"
    assert traza.entity == "usuario"
    assert traza.rol == "Coordinacion"
    assert traza.created_at is not None


def test_record_audit_guarda_valores_anterior_y_nuevo(db_session: Session):
    record_audit(
        db_session,
        actor="ana",
        action="UPDATE",
        entity="usuario",
        entity_id="7",
        valor_anterior='{"activo": true}',
        valor_nuevo='{"activo": false}',
    )
    db_session.flush()
    traza = db_session.scalars(select(AuditLog).where(AuditLog.entity_id == "7")).one()
    assert traza.valor_anterior == '{"activo": true}'
    assert traza.valor_nuevo == '{"activo": false}'


def test_record_audit_no_hace_commit_se_integra_en_la_transaccion(db_session: Session):
    # record_audit añade a la sesión pero NO commitea: la traza vive o muere con la
    # transacción del caller (CEPA-003 TC-003-05: sin trazas parciales).
    record_audit(db_session, actor="x", action="DELETE", entity="prueba", entity_id="1")
    assert any(isinstance(obj, AuditLog) for obj in db_session.new)
