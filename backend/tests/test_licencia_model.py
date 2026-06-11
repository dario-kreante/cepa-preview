from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric

from app.models.licencia import LicenciaMedica


def test_tabla_y_columnas():
    tabla = LicenciaMedica.__table__
    assert tabla.name == "licencia_medica"
    columnas_esperadas = {
        "id",
        "ingreso_id",
        "folio_lm",
        "tipo_lm",
        "tipo_reposo",
        "fecha_inicio",
        "fecha_termino",
        "fecha_emision",
        "inicio_reposo",
        "fin_reposo",
        "cantidad_dias",
        "indicacion_reposo",
        "diagnostico",
        "origen",
        "envio_isl",
        "fecha_envio_isl",
        "eeag_gaf",
        "observaciones",
        "anulada",
        "created_at",
        "updated_at",
    }
    assert set(tabla.columns.keys()) == columnas_esperadas


def test_reglas_portabilidad_identificadores():
    tabla = LicenciaMedica.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"'{nombre}' debe ir en minúscula"
        assert len(nombre) <= 30, f"'{nombre}' supera 30 chars (Oracle limit)"


def test_tipos_y_pk():
    cols = LicenciaMedica.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    # fechas de calendario sin hora
    assert isinstance(cols["fecha_inicio"].type, Date)
    assert isinstance(cols["fecha_termino"].type, Date)
    assert isinstance(cols["fecha_emision"].type, Date)
    assert isinstance(cols["inicio_reposo"].type, Date)
    assert isinstance(cols["fin_reposo"].type, Date)
    # enteros
    assert isinstance(cols["cantidad_dias"].type, Integer)
    # timestamps con zona
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True
    # bool anulada
    assert isinstance(cols["anulada"].type, Boolean)
    # GAF como Numeric para no perder precisión en Oracle
    assert isinstance(cols["eeag_gaf"].type, (Integer, Numeric))


def test_fk_ingreso_existe():
    tabla = LicenciaMedica.__table__
    fks = list(tabla.columns["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"


def test_anulada_default_false():
    assert LicenciaMedica.__table__.columns["anulada"].nullable is False
