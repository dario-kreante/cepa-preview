from sqlalchemy import BigInteger, Date, String

from app.models.oda import Oda


def test_columnas_oda():
    assert set(Oda.__table__.columns.keys()) == {
        "id",
        "ingreso_id",
        "identificador",
        "fecha_registro",   # EPIC-09 D4: campo añadido para reporte ODAS vencidas
        "fecha_vencimiento",
        "vigente",
        "created_at",
    }


def test_portabilidad_y_tipos_oda():
    tabla = Oda.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30
    assert isinstance(tabla.columns["id"].type, BigInteger)
    assert isinstance(tabla.columns["fecha_vencimiento"].type, Date)
    assert isinstance(tabla.columns["identificador"].type, String)


def test_fk_ingreso():
    fks = list(Oda.__table__.columns["ingreso_id"].foreign_keys)
    assert fks[0].column.table.name == "ingreso"
