"""Migración 1580: catálogos de fármacos por convenio. Sube y baja sin dejar tablas.

Archivo aparte: el downgrade no puede correr con una sesión de prueba abierta.
"""

from sqlalchemy import inspect

from app.db.session import engine


def test_la_migracion_sube_y_baja():
    from alembic import command  # noqa: PLC0415

    from tests.conftest import _alembic_config  # noqa: PLC0415

    cfg = _alembic_config()
    command.downgrade(cfg, "1570")
    try:
        # has_table y no get_table_names: en el Oracle del CI este último vuelve vacío.
        assert not inspect(engine).has_table("farmaco_canasta")
        assert not inspect(engine).has_table("farmaco_externalizado")
    finally:
        command.upgrade(cfg, "head")
    assert inspect(engine).has_table("farmaco_canasta")
    assert inspect(engine).has_table("farmaco_externalizado")
