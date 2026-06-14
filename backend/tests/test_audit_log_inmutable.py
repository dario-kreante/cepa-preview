import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def test_update_sobre_audit_log_es_rechazado_por_la_bd(db_session: Session):
    db_session.add(AuditLog(actor="tester", action="CREATE", entity="prueba"))
    db_session.flush()
    with pytest.raises(DatabaseError):
        db_session.execute(text("UPDATE audit_log SET actor = 'hacker' WHERE actor = 'tester'"))
        db_session.flush()


def test_delete_sobre_audit_log_es_rechazado_por_la_bd(db_session: Session):
    db_session.add(AuditLog(actor="tester2", action="CREATE", entity="prueba"))
    db_session.flush()
    with pytest.raises(DatabaseError):
        db_session.execute(text("DELETE FROM audit_log WHERE actor = 'tester2'"))
        db_session.flush()
