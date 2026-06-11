from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String

from app.models.usuario import Usuario


def test_tabla_y_columnas_esperadas():
    tabla = Usuario.__table__
    assert tabla.name == "usuario"
    assert set(tabla.columns.keys()) == {
        "id",
        "username",
        "nombre",
        "hashed_password",
        "rol",
        "activo",
        "intentos_fallidos",
        "bloqueado_hasta",
        "email",  # DD-C (CEPA-102): correo para notificaciones de alerta
        "created_at",
    }


def test_reglas_de_portabilidad_en_identificadores():
    tabla = Usuario.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera el límite de 30 chars de Oracle"


def test_tipos_genericos_y_pk_identity():
    cols = Usuario.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["username"].type, String)
    assert isinstance(cols["rol"].type, String)
    assert isinstance(cols["activo"].type, Boolean)
    assert isinstance(cols["intentos_fallidos"].type, Integer)
    assert isinstance(cols["bloqueado_hasta"].type, DateTime)
    assert cols["bloqueado_hasta"].type.timezone is True
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True


def test_username_es_unico():
    assert Usuario.__table__.columns["username"].unique is True
