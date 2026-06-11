from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, String

from app.models.audit_log import AuditLog


def test_tabla_y_columnas_esperadas():
    tabla = AuditLog.__table__
    assert tabla.name == "audit_log"
    assert set(tabla.columns.keys()) == {
        "id",
        "actor",
        "rol",
        "action",
        "entity",
        "entity_id",
        "valor_anterior",
        "valor_nuevo",
        "created_at",
    }


def test_reglas_de_portabilidad_en_identificadores():
    tabla = AuditLog.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera el límite de 30 chars de Oracle"


def test_tipos_genericos_y_pk_identity():
    cols = AuditLog.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None  # PK por Identity, no SERIAL ni secuencia manual
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["actor"].type, String)
    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True  # fechas con zona (UTC)


def test_default_created_at_es_utc():
    default = AuditLog.__table__.columns["created_at"].default
    assert default is not None and default.is_callable
    valor = default.arg(None)
    assert valor.tzinfo == timezone.utc
    assert isinstance(valor, datetime)
