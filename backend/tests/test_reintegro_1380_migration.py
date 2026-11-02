"""Migración 1380 (QA-008): caso_reintegro con razón social, tipo de trabajador y
sexo/edad opcionales."""

from sqlalchemy import inspect

from app.db.session import engine


def _columnas() -> dict[str, dict]:
    return {c["name"]: c for c in inspect(engine).get_columns("caso_reintegro")}


def test_columnas_nuevas_en_bd():
    cols = _columnas()
    assert cols["razon_social"]["nullable"] is True
    assert cols["tipo_trabajador"]["nullable"] is True


def test_sexo_y_edad_nullable_en_bd():
    cols = _columnas()
    assert cols["sexo"]["nullable"] is True
    assert cols["edad"]["nullable"] is True
