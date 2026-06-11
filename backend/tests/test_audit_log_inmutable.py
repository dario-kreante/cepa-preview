import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session


def test_update_sobre_audit_log_es_rechazado_por_la_bd(db_session: Session):
    db_session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, created_at) "
            "VALUES ('tester', 'CREATE', 'prueba', now())"
        )
    )
    db_session.flush()
    with pytest.raises(DatabaseError):
        db_session.execute(text("UPDATE audit_log SET actor = 'hacker' WHERE actor = 'tester'"))
        db_session.flush()


def test_delete_sobre_audit_log_es_rechazado_por_la_bd(db_session: Session):
    db_session.execute(
        text(
            "INSERT INTO audit_log (actor, action, entity, created_at) "
            "VALUES ('tester2', 'CREATE', 'prueba', now())"
        )
    )
    db_session.flush()
    with pytest.raises(DatabaseError):
        db_session.execute(text("DELETE FROM audit_log WHERE actor = 'tester2'"))
        db_session.flush()
