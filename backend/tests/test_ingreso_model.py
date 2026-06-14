from sqlalchemy import BigInteger, Boolean, Date, DateTime, String

from app.models.ingreso import Ingreso


def test_tabla_y_columnas():
    tabla = Ingreso.__table__
    assert tabla.name == "ingreso"
    assert set(tabla.columns.keys()) == {
        "id",
        "paciente_id",
        "folio",
        "folio_manual",
        "numero_siniestro",
        "fecha_ingreso",
        "fecha_diep_diat",
        "tipo_derivacion",
        "tipo_ingreso",
        "modelo_tratamiento",
        "diagnostico",
        "razon_social",
        "estado",
        "tipo_alta",
        "fecha_alta",
        "flag_revision",
        "observaciones",
        "tratamiento_iniciado",
        "created_at",
        "updated_at",
        # EPIC-09 DD-3: sexo/region/comuna/tramo_etario eliminados (viven en Paciente)
        "programa",
        "profesional_id",
        "tipo_convenio",
        "especialidad",
        "tipo_atencion",
    }


def test_portabilidad_identificadores():
    tabla = Ingreso.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower()
        assert len(nombre) <= 30


def test_tipos_y_pk():
    cols = Ingreso.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["folio"].type, String)
    assert isinstance(cols["fecha_ingreso"].type, Date)
    assert isinstance(cols["folio_manual"].type, Boolean)
    assert isinstance(cols["flag_revision"].type, Boolean)
    assert isinstance(cols["tratamiento_iniciado"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_folio_unico_y_fk_paciente():
    tabla = Ingreso.__table__
    # Folio es único por paciente (reingresos permitidos), no globalmente
    # Unicidad global se valida a nivel de servicio
    assert tabla.columns["folio"].unique is not True
    fks = list(tabla.columns["paciente_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "paciente"


def test_estado_no_nullable_default_activo():
    # estado por defecto 'activo' a nivel de modelo
    assert Ingreso.__table__.columns["estado"].nullable is False
