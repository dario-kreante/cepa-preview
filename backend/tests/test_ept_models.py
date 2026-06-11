from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Date, DateTime, String

from app.models.ept import CasoEpt, ContactoEpt


def test_tabla_caso_ept_columnas():
    tabla = CasoEpt.__table__
    assert tabla.name == "caso_ept"
    assert set(tabla.columns.keys()) == {
        "id",
        "ingreso_id",
        "mes",
        "fecha_ingreso_ept",
        "nombre_trabajador",
        "rut_trabajador",
        "region_trabajador",
        "eista",
        "factor_riesgo",
        "corresponde_ept",
        "estado",
        "razon_social",
        "unidad_cargo_horario",
        "created_at",
        "updated_at",
    }


def test_portabilidad_caso_ept():
    tabla = CasoEpt.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"{nombre!r} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre!r} supera 30 chars"


def test_pk_identity_caso_ept():
    cols = CasoEpt.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)


def test_fk_a_ingreso():
    fks = list(CasoEpt.__table__.columns["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"


def test_corresponde_ept_es_boolean():
    col = CasoEpt.__table__.columns["corresponde_ept"]
    assert isinstance(col.type, Boolean)


def test_tabla_contacto_ept_columnas():
    tabla = ContactoEpt.__table__
    assert tabla.name == "contacto_ept"
    assert set(tabla.columns.keys()) == {
        "id",
        "caso_ept_id",
        "correo",
        "created_at",
    }


def test_portabilidad_contacto_ept():
    tabla = ContactoEpt.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30


def test_caso_ept_fecha_ingreso_es_date():
    col = CasoEpt.__table__.columns["fecha_ingreso_ept"]
    assert isinstance(col.type, Date)


def test_caso_ept_created_at_utc():
    default = CasoEpt.__table__.columns["created_at"].default
    assert default is not None and default.is_callable
    valor = default.arg(None)
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
