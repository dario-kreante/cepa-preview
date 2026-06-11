"""Tests del modelo AlertaNotif (CEPA-100, CEPA-101).

Desviación 1: el modelo usa AlertaNotif/alerta_notif en lugar de Alerta/alerta
para coexistir con app.models.farmacos.Alerta (EPIC-02).
"""

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String

from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import AlertaNotif


def test_tabla_alerta_notif_nombre_y_columnas():
    tabla = AlertaNotif.__table__
    assert tabla.name == "alerta_notif"
    columnas = set(tabla.columns.keys())
    assert columnas == {
        "id",
        "tipo",
        "estado",
        "caso_id",
        "caso_tipo",
        "usuario_id",
        "plazo_objetivo",
        "ventana_dias",
        "generada_en",
        "resuelta_en",
        "email_enviado",
    }


def test_reglas_portabilidad_alerta_notif():
    tabla = AlertaNotif.__table__
    nombres = [tabla.name, *tabla.columns.keys()]
    for nombre in nombres:
        assert nombre == nombre.lower(), f"{nombre} debe ir en minúscula"
        assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pk_identity_y_tipos_genericos_alerta_notif():
    cols = AlertaNotif.__table__.columns
    assert cols["id"].primary_key
    assert cols["id"].identity is not None
    assert isinstance(cols["id"].type, BigInteger)
    assert isinstance(cols["tipo"].type, String)
    assert isinstance(cols["estado"].type, String)
    assert isinstance(cols["generada_en"].type, DateTime)
    assert cols["generada_en"].type.timezone is True


def test_enum_tipo_alerta_contiene_todos_los_tipos_rn1():
    tipos = {t.value for t in TipoAlerta}
    assert "control_medico" in tipos
    assert "vencimiento_licencia" in tipos
    assert "plazo_ept" in tipos
    assert "plazo_isl" in tipos
    assert "consentimiento_pendiente" in tipos
    assert "receta_por_renovar" in tipos
    assert "oda_por_vencer" in tipos
    assert len(tipos) == 7


def test_enum_estado_alerta():
    assert {e.value for e in EstadoAlerta} == {"pendiente", "leida", "resuelta"}
