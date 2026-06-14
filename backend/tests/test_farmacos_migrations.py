from sqlalchemy import inspect

from app.db.session import engine


def test_tablas_de_farmacos_existen():
    insp = inspect(engine)
    for nombre in [
        "reg_farmacologico",
        "esquema_indicacion",
        "receta",
        "seguim_tratamiento",
        "alerta",
    ]:
        assert insp.has_table(nombre), f"Tabla {nombre!r} no encontrada tras upgrade head"
