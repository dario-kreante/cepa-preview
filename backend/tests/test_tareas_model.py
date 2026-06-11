"""Tests del modelo TareaItem (CEPA-103)."""

from sqlalchemy import BigInteger

from app.domain.enums_alertas import EstadoTarea
from app.models.tareas import TareaItem


def test_tabla_tarea_item_nombre_y_columnas():
    tabla = TareaItem.__table__
    assert tabla.name == "tarea_item"
    cols = set(tabla.columns.keys())
    assert cols == {
        "id",
        "titulo",
        "descripcion",
        "estado",
        "tipo_tarea",
        "caso_id",
        "caso_tipo",
        "usuario_id",
        "creada_en",
        "completada_en",
        "completada_por",
    }


def test_reglas_portabilidad_tarea_item():
    tabla = TareaItem.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pk_identity_tarea_item():
    cols = TareaItem.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)


def test_enum_estado_tarea():
    assert {e.value for e in EstadoTarea} == {"pendiente", "en_progreso", "completada"}
