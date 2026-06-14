import pytest
from pydantic import ValidationError

from app.schemas.ept import CasoEptCreate


def test_rut_invalido_rechazado():
    """CA-2 CEPA-030: RUT con DV inválido no permite crear el schema."""
    with pytest.raises(ValidationError) as exc:
        CasoEptCreate(
            ingreso_id=1,
            mes="2026-06",
            fecha_ingreso_ept="2026-06-01",
            nombre_trabajador="Pedro Soto",
            rut_trabajador="12.345.678-0",  # DV inválido
            region_trabajador="Maule",
            eista="Ana González",
            factor_riesgo="carga",
            corresponde_ept=True,
        )
    assert "rut" in str(exc.value).lower()


def test_schema_valido_acepta_corresponde_ept_false():
    """CA-4 CEPA-030: corresponde_ept=False no exige datos de proceso."""
    caso = CasoEptCreate(
        ingreso_id=1,
        mes="2026-06",
        fecha_ingreso_ept="2026-06-01",
        nombre_trabajador="Pedro Soto",
        rut_trabajador="12.345.678-5",
        region_trabajador="Maule",
        eista="Ana González",
        factor_riesgo="carga",
        corresponde_ept=False,
    )
    assert caso.corresponde_ept is False


def test_correos_invalidos_rechazados():
    """CA-3 CEPA-030: formato de correo validado en contactos."""
    from app.schemas.ept import ContactoEptCreate

    with pytest.raises(ValidationError):
        ContactoEptCreate(caso_ept_id=1, correo="no_es_un_correo")


def test_correo_valido_aceptado():
    from app.schemas.ept import ContactoEptCreate

    c = ContactoEptCreate(caso_ept_id=1, correo="rrhh@empresa.cl")
    assert c.correo == "rrhh@empresa.cl"


def test_factor_riesgo_fuera_de_lista_rechazado():
    """Factor de riesgo no válido -> ValidationError."""
    with pytest.raises(ValidationError):
        CasoEptCreate(
            ingreso_id=1,
            mes="2026-06",
            fecha_ingreso_ept="2026-06-01",
            nombre_trabajador="Pedro Soto",
            rut_trabajador="12.345.678-5",
            region_trabajador="Maule",
            eista="Ana González",
            factor_riesgo="invalido_xyz",
            corresponde_ept=True,
        )
