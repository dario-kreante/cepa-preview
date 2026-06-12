from sqlalchemy import inspect

from app.db.session import engine


def test_la_migracion_crea_la_tabla_audit_log():
    assert inspect(engine).has_table("audit_log")
