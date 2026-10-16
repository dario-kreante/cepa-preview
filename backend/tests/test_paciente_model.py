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
        "salutem_persona_id",
        "estado_registro",
        "origen",
        "motivo_descarte",
        "descartado_por",
        "descartado_en",
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


def test_un_paciente_nuevo_queda_completo_y_de_origen_sige(db_session):
    p = Paciente(rut="11111111-1", nombre="Ana Pérez", sexo="F", edad=30, region="Maule")
    db_session.add(p)
    db_session.flush()
    db_session.refresh(p)
    assert p.estado_registro == "completo"
    assert p.origen == "SIGE"


def test_un_borrador_admite_rut_sexo_edad_y_region_nulos(db_session):
    p = Paciente(
        nombre="Borrador Salutem",
        estado_registro="pendiente_folio",
        origen="SALUTEM",
        salutem_persona_id=1180505,
    )
    db_session.add(p)
    db_session.flush()
    assert p.id is not None
    assert p.rut is None and p.sexo is None and p.edad is None and p.region is None


def test_dos_borradores_sin_rut_no_chocan_por_unique(db_session):
    db_session.add(Paciente(nombre="Borrador Uno", estado_registro="pendiente_folio", origen="SALUTEM"))
    db_session.add(Paciente(nombre="Borrador Dos", estado_registro="pendiente_folio", origen="SALUTEM"))
    db_session.flush()
