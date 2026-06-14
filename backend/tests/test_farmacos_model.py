from sqlalchemy import BigInteger, Boolean, DateTime, String

from app.models.farmacos import RegistroFarmacologico


def test_tabla_y_columnas_reg_farmacologico():
    tabla = RegistroFarmacologico.__table__
    assert tabla.name == "reg_farmacologico"
    assert set(tabla.columns.keys()) == {
        "id",
        "ingreso_id",
        "medico_tratante",
        "estado_farmacologico",
        "antecedentes_previos",
        "tratamiento_previo",
        "activo",
        "created_at",
        "updated_at",
    }


def test_portabilidad_identificadores_reg():
    tabla = RegistroFarmacologico.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pk_identity_y_tipos_reg():
    cols = RegistroFarmacologico.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["medico_tratante"].type, String)
    assert isinstance(cols["estado_farmacologico"].type, String)
    assert isinstance(cols["activo"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_ingreso_id_es_unique_en_reg():
    """Un folio puede tener a lo sumo un registro farmacológico activo (CEPA-020 RN-4)."""
    tabla = RegistroFarmacologico.__table__
    assert tabla.columns["ingreso_id"].unique is True


def test_fk_a_ingreso():
    cols = RegistroFarmacologico.__table__.columns
    fks = list(cols["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"
