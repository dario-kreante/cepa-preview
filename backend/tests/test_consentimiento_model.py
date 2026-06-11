from sqlalchemy import DateTime, String

from app.models.consentimiento import Consentimiento


def test_columnas_consentimiento():
    assert set(Consentimiento.__table__.columns.keys()) == {
        "id",
        "ingreso_id",
        "estado",
        "evidencia_ref",
        "fecha_firma",
        "created_at",
        "updated_at",
    }


def test_portabilidad_y_tipos():
    tabla = Consentimiento.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30
    assert isinstance(tabla.columns["estado"].type, String)
    assert isinstance(tabla.columns["created_at"].type, DateTime)
    assert tabla.columns["created_at"].type.timezone is True


def test_fk_ingreso_unica():
    cols = Consentimiento.__table__.columns
    assert cols["ingreso_id"].unique is True
    fks = list(cols["ingreso_id"].foreign_keys)
    assert fks[0].column.table.name == "ingreso"
