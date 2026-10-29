import pytest
from pydantic import ValidationError

from app.schemas.reintegro import CasoReintegroCreate


def _payload(**over):
    base = {
        "ingreso_id": 1,
        "rut": "12.345.678-5",
        "nombre": "Juan Pérez",
        "tipo_derivacion": "DIAT",
        "fecha_caso": "2026-06-10",
        "sexo": "M",
        "edad": 40,
        "region": "Maule",
    }
    base.update(over)
    return base


# TC-040-01: campos obligatorios completos — crea OK
def test_schema_valido_acepta_campos_obligatorios():
    obj = CasoReintegroCreate(**_payload())
    assert obj.rut == "123456785"  # normalizado por validador
    assert obj.nombre == "Juan Pérez"


# TC-040-03: RUT con DV inválido → ValidationError
def test_schema_rechaza_rut_invalido():
    with pytest.raises(ValidationError) as exc_info:
        CasoReintegroCreate(**_payload(rut="12.345.678-0"))
    assert "rut" in str(exc_info.value).lower()


# TC-040-04: campos obligatorios faltantes → ValidationError
def test_schema_rechaza_faltan_obligatorios():
    datos = _payload()
    del datos["region"]
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**datos)


# TC-040-04 (bis): zona geográfica obligatoria (D6)
def test_schema_exige_region():
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(region=None))


# QA-008 (QA UTalca 22-10): sexo y edad ya no se piden en el alta (se copian del paciente)
def test_schema_sexo_y_edad_opcionales():
    datos = _payload()
    del datos["sexo"]
    del datos["edad"]
    obj = CasoReintegroCreate(**datos)
    assert obj.sexo is None
    assert obj.edad is None


# QA-008: tipo de trabajador de lista cerrada
def test_schema_tipo_trabajador():
    assert CasoReintegroCreate(**_payload(tipo_trabajador="independiente")).tipo_trabajador.value == "independiente"
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(tipo_trabajador="honorarios"))


# TC-040-04 (bis): tipo_derivacion fuera de lista cerrada D4 → ValidationError
def test_schema_rechaza_tipo_derivacion_invalido():
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(tipo_derivacion="SOCORRO"))


# TC-040-04 (bis): tipo_derivacion de la lista D4 → OK
def test_schema_acepta_tipo_derivacion_reingreso_fump():
    obj = CasoReintegroCreate(**_payload(tipo_derivacion="Reingreso FUMP"))
    assert obj.tipo_derivacion.value == "Reingreso FUMP"
