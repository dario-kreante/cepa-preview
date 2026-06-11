from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, String

from app.models.paciente import Paciente


def test_tabla_y_columnas():
    tabla = Paciente.__table__
    assert tabla.name == "paciente"
    assert set(tabla.columns.keys()) == {
        "id",
        "rut",
        "nombre",
        "sexo",
        "edad",
        "region",
        "comuna",
        "telefono",
        "correo",
        "created_at",
        "updated_at",
    }


def test_reglas_portabilidad_identificadores():
    tabla = Paciente.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30


def test_pk_identity_y_tipos():
    cols = Paciente.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["rut"].type, String)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_rut_es_unico():
    assert Paciente.__table__.columns["rut"].unique is True


def test_default_created_at_utc():
    default = Paciente.__table__.columns["created_at"].default
    # SQLAlchemy 2.0 defaults can be either callables or have .arg()
    # Try calling it directly if .arg() requires context
    try:
        valor = default.arg()
    except TypeError:
        valor = default.arg(None)
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
