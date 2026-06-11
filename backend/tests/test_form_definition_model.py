from sqlalchemy import BigInteger, Boolean, DateTime, Integer

from app.models.form_definition import FieldDef, FormDefinition, FormVersion


def test_form_definition_columnas():
    tabla = FormDefinition.__table__
    assert tabla.name == "form_definition"
    assert set(tabla.columns.keys()) == {"id", "form_key", "created_at"}


def test_form_version_columnas():
    tabla = FormVersion.__table__
    assert tabla.name == "form_version"
    assert set(tabla.columns.keys()) == {
        "id",
        "form_def_id",
        "version_num",
        "status",
        "published_at",
        "created_by",
        "created_at",
    }


def test_field_def_columnas():
    tabla = FieldDef.__table__
    assert tabla.name == "field_def"
    assert set(tabla.columns.keys()) == {
        "id",
        "form_version_id",
        "field_key",
        "label",
        "field_type",
        "required",
        "system_locked",
        "domain_values",
        "display_order",
        "active",
    }


def test_portabilidad_identificadores():
    for modelo in (FormDefinition, FormVersion, FieldDef):
        tabla = modelo.__table__
        for nombre in [tabla.name, *tabla.columns.keys()]:
            assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
            assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_tipos_portables():
    cols_fd = FormDefinition.__table__.columns
    assert isinstance(cols_fd["id"].type, BigInteger)
    assert cols_fd["id"].identity is not None

    cols_fv = FormVersion.__table__.columns
    assert isinstance(cols_fv["id"].type, BigInteger)
    assert isinstance(cols_fv["version_num"].type, Integer)
    assert isinstance(cols_fv["published_at"].type, DateTime)
    assert cols_fv["published_at"].type.timezone is True

    cols_field = FieldDef.__table__.columns
    assert isinstance(cols_field["required"].type, Boolean)
    assert isinstance(cols_field["system_locked"].type, Boolean)
    assert isinstance(cols_field["active"].type, Boolean)
    # domain_values: JSON genérico (portable PG/Oracle)
    from sqlalchemy import JSON
    assert isinstance(cols_field["domain_values"].type, JSON)


def test_field_def_fk_a_form_version():
    fks = list(FieldDef.__table__.columns["form_version_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "form_version"


def test_form_version_fk_a_form_definition():
    fks = list(FormVersion.__table__.columns["form_def_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "form_definition"
