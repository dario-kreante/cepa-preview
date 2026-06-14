from sqlalchemy import BigInteger, Boolean, Date, DateTime, String

from app.models.reintegro import CasoReintegro, Reca


# ── CasoReintegro ──────────────────────────────────────────────────────────

def test_caso_reintegro_tabla_y_columnas():
    tabla = CasoReintegro.__table__
    assert tabla.name == "caso_reintegro"
    esperadas = {
        "id",
        "ingreso_id",
        "rut",
        "nombre",
        "tipo_derivacion",
        "fecha_caso",
        "sexo",
        "edad",
        "region",
        "comuna",
        "rubro_empleador",
        "estado_reintegro",
        "fecha_reintegro",
        "remitido_isl",
        "alta_medica",
        "fecha_alta_medica",
        "alta_psicologica",
        "fecha_alta_psico",
        "tipo_alta",
        "observaciones",
        "created_at",
        "updated_at",
    }
    assert set(tabla.columns.keys()) == esperadas


def test_caso_reintegro_portabilidad():
    tabla = CasoReintegro.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"'{nombre}' debe ir en minúscula"
        assert len(nombre) <= 30, f"'{nombre}' supera 30 chars (Oracle)"


def test_caso_reintegro_tipos_y_pk():
    cols = CasoReintegro.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["rut"].type, String)
    assert isinstance(cols["fecha_caso"].type, Date)
    assert isinstance(cols["remitido_isl"].type, Boolean)
    assert isinstance(cols["alta_medica"].type, Boolean)
    assert isinstance(cols["alta_psicologica"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_caso_reintegro_fk_ingreso():
    cols = CasoReintegro.__table__.columns
    fks = list(cols["ingreso_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "ingreso"


# ── Reca ───────────────────────────────────────────────────────────────────

def test_reca_tabla_y_columnas():
    tabla = Reca.__table__
    assert tabla.name == "reca"
    esperadas = {
        "id",
        "caso_reintegro_id",
        "fecha_reca",
        "tipo_reca",
        "numero_reca",
        "riesgos_calificados",
        "razon_social",
        "solicita_medidas",
        "detalle_medidas",
        "fecha_medidas",
        "verifica_medidas",
        "detalle_verificacion",
        "fecha_verificacion",
        "created_at",
        "updated_at",
    }
    assert set(tabla.columns.keys()) == esperadas


def test_reca_portabilidad():
    tabla = Reca.__table__
    for nombre in [tabla.name, *tabla.columns.keys()]:
        assert nombre == nombre.lower(), f"'{nombre}' debe ir en minúscula"
        assert len(nombre) <= 30, f"'{nombre}' supera 30 chars (Oracle)"


def test_reca_tipos_y_pk():
    cols = Reca.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["fecha_reca"].type, Date)
    assert isinstance(cols["solicita_medidas"].type, Boolean)
    assert isinstance(cols["verifica_medidas"].type, Boolean)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_reca_numero_unico_por_caso():
    # La unicidad (numero_reca, caso_reintegro_id) se aplica con UniqueConstraint
    tabla = Reca.__table__
    nombres_constraints = [c.name for c in tabla.constraints]
    assert any("uq_reca_numero_caso" in (n or "") for n in nombres_constraints)


def test_reca_fk_caso_reintegro():
    cols = Reca.__table__.columns
    fks = list(cols["caso_reintegro_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "caso_reintegro"
