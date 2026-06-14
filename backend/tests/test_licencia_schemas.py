import pytest
from pydantic import ValidationError

from app.schemas.licencia import LicenciaCreate, LicenciaISLUpdate


# CA-2 / RN-4 CEPA-070: fecha_termino >= fecha_inicio
def test_fecha_termino_anterior_a_inicio_rechazada():
    with pytest.raises(ValidationError) as exc_info:
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio="2026-06-15",
            fecha_termino="2026-06-01",  # anterior a inicio
            fecha_emision="2026-06-10",
            inicio_reposo="2026-06-15",
            fin_reposo="2026-06-29",
            cantidad_dias=15,
            diagnostico="F32.1",
        )
    errs = exc_info.value.errors()
    assert any("fecha_termino" in str(e["loc"]) or "termino" in e["msg"].lower() for e in errs)


# RN-4 CEPA-070: fecha_emision <= fecha_inicio
def test_fecha_emision_posterior_a_inicio_rechazada():
    with pytest.raises(ValidationError):
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio="2026-06-10",
            fecha_termino="2026-06-24",
            fecha_emision="2026-06-15",  # posterior a inicio
            inicio_reposo="2026-06-10",
            fin_reposo="2026-06-24",
            cantidad_dias=15,
            diagnostico="F32.1",
        )


# RN-4 CEPA-070: fin_reposo >= inicio_reposo
def test_fin_reposo_anterior_a_inicio_reposo_rechazado():
    with pytest.raises(ValidationError):
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="1",
            tipo_reposo="total",
            fecha_inicio="2026-06-10",
            fecha_termino="2026-06-24",
            fecha_emision="2026-06-08",
            inicio_reposo="2026-06-15",
            fin_reposo="2026-06-10",  # anterior a inicio_reposo
            cantidad_dias=15,
            diagnostico="F32.1",
        )


# TC-070-05 / RN-3: tipo_lm fuera de catálogo rechazado
def test_tipo_lm_invalido_rechazado():
    with pytest.raises(ValidationError):
        LicenciaCreate(
            ingreso_id=1,
            tipo_lm="3",  # no está en {1, 5, 6}
            tipo_reposo="total",
            fecha_inicio="2026-06-10",
            fecha_termino="2026-06-24",
            fecha_emision="2026-06-08",
            inicio_reposo="2026-06-10",
            fin_reposo="2026-06-24",
            cantidad_dias=15,
            diagnostico="F32.1",
        )


# TC-073-05 / RN-1 CEPA-073: EEAG fuera de rango 1-100 rechazado
def test_eeag_gaf_fuera_de_rango_rechazado():
    with pytest.raises(ValidationError):
        LicenciaISLUpdate(envio_isl="enviado", fecha_envio_isl="2026-06-02", eeag_gaf=150)


def test_eeag_gaf_cero_rechazado():
    with pytest.raises(ValidationError):
        LicenciaISLUpdate(envio_isl="enviado", fecha_envio_isl="2026-06-02", eeag_gaf=0)


# TC-073-02 / RN-2: estado=enviado sin fecha rechazado
def test_isl_enviado_sin_fecha_rechazado():
    with pytest.raises(ValidationError):
        LicenciaISLUpdate(envio_isl="enviado", fecha_envio_isl=None)


# Schema válido: no lanza excepción
def test_schema_valido_acepta():
    lm = LicenciaCreate(
        ingreso_id=1,
        tipo_lm="1",
        tipo_reposo="total",
        fecha_inicio="2026-06-01",
        fecha_termino="2026-06-15",
        fecha_emision="2026-05-30",
        inicio_reposo="2026-06-01",
        fin_reposo="2026-06-15",
        cantidad_dias=15,
        diagnostico="F32.1",
    )
    assert lm.tipo_lm.value == "1"
    assert lm.cantidad_dias == 15
