from sqlalchemy import inspect

from app.db.session import engine


def test_tablas_de_farmacos_existen():
    tablas = inspect(engine).get_table_names()
    for nombre in [
        "reg_farmacologico",
        "esquema_indicacion",
        "receta",
        "seguim_tratamiento",
        "alerta",
    ]:
        assert nombre in tablas, f"Tabla {nombre!r} no encontrada tras upgrade head"
