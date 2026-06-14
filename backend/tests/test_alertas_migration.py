"""Tests de migración para la tabla alerta_notif (CEPA-100, Desviación 1).

La tabla se llama alerta_notif (no alerta) para coexistir con la tabla alerta de EPIC-02.
"""

from sqlalchemy import inspect

from app.db.session import engine


def test_migracion_crea_tabla_alerta_notif():
    assert inspect(engine).has_table("alerta_notif")


def test_columnas_alerta_notif_en_bd():
    cols = {c["name"] for c in inspect(engine).get_columns("alerta_notif")}
    assert cols == {
        "id",
        "tipo",
        "estado",
        "caso_id",
        "caso_tipo",
        "usuario_id",
        "plazo_objetivo",
        "ventana_dias",
        "generada_en",
        "resuelta_en",
        "email_enviado",
    }
