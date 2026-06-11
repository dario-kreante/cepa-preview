from datetime import datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Integer, String

from app.models.control_medico import ControlMedico


def test_tabla_nombre_y_columnas_base():
    tabla = ControlMedico.__table__
    assert tabla.name == "control_medico"
    columnas = set(tabla.columns.keys())
    # columnas de CEPA-060
    assert {
        "id",
        "ingreso_id",
        "fecha_control",
        "semana_control",
        "medico_tratante",
        "region_derivacion",
        "created_at",
        "updated_at",
    }.issubset(columnas)


def test_portabilidad_identificadores():
    tabla = ControlMedico.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"{nombre!r} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre!r} supera 30 chars (Oracle)"


def test_pk_identity_biginteger():
    cols = ControlMedico.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)


def test_tipos_genericos():
    cols = ControlMedico.__table__.columns
    assert isinstance(cols["fecha_control"].type, Date)
    assert isinstance(cols["semana_control"].type, Integer)
    assert isinstance(cols["medico_tratante"].type, String)
    assert isinstance(cols["region_derivacion"].type, String)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True
    assert isinstance(cols["updated_at"].type, DateTime)
    assert cols["updated_at"].type.timezone is True


def test_fk_a_ingreso():
    cols = ControlMedico.__table__.columns
    fks = list(cols["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"


def test_default_created_at_es_utc():
    default = ControlMedico.__table__.columns["created_at"].default
    assert default is not None and default.is_callable
    valor = default.arg(None)
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
