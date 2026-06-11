from sqlalchemy import inspect

from app.db.session import engine


def test_la_migracion_crea_la_tabla_audit_log():
    tablas = inspect(engine).get_table_names()
    assert "audit_log" in tablas
