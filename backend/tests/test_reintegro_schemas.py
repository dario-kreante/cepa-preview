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
    del datos["sexo"]
    del datos["region"]
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**datos)


# TC-040-04 (bis): sexo y zona geográfica obligatorios (D5/D6)
def test_schema_exige_sexo_y_region():
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(sexo=None))
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(region=None))


# TC-040-04 (bis): tipo_derivacion fuera de lista cerrada D4 → ValidationError
def test_schema_rechaza_tipo_derivacion_invalido():
    with pytest.raises(ValidationError):
        CasoReintegroCreate(**_payload(tipo_derivacion="SOCORRO"))


# TC-040-04 (bis): tipo_derivacion de la lista D4 → OK
def test_schema_acepta_tipo_derivacion_reingreso_fump():
    obj = CasoReintegroCreate(**_payload(tipo_derivacion="Reingreso FUMP"))
    assert obj.tipo_derivacion.value == "Reingreso FUMP"
