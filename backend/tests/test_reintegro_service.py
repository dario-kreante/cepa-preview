"""Tests unitarios del servicio de reintegro — reglas de negocio puras."""

import datetime
import pytest
from fastapi import HTTPException

from app.services.reintegro import (
    validar_coherencia_reca,
    validar_coherencia_medidas,
    validar_coherencia_cierre,
)


# RN-3 CEPA-041: fecha_verificacion >= fecha_medidas >= fecha_reca
# TC-041-04: verificación anterior a medida → rechazado
def test_coherencia_medidas_rechaza_verificacion_anterior():
    fecha_reca = datetime.date(2026, 3, 1)
    fecha_medidas = datetime.date(2026, 3, 10)
    fecha_verificacion = datetime.date(2026, 3, 5)  # anterior a fecha_medidas
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_medidas(fecha_reca, fecha_medidas, fecha_verificacion)
    assert exc_info.value.status_code == 422


# TC-041-02: verificación posterior a medida → OK
def test_coherencia_medidas_acepta_verificacion_posterior():
    fecha_reca = datetime.date(2026, 3, 1)
    fecha_medidas = datetime.date(2026, 3, 10)
    fecha_verificacion = datetime.date(2026, 3, 25)
    # no lanza excepción
    validar_coherencia_medidas(fecha_reca, fecha_medidas, fecha_verificacion)


# RN-3 CEPA-041: fecha_medidas >= fecha_reca
def test_coherencia_medidas_rechaza_medida_anterior_a_reca():
    fecha_reca = datetime.date(2026, 3, 10)
    fecha_medidas = datetime.date(2026, 3, 5)   # anterior a RECA
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_medidas(fecha_reca, fecha_medidas, None)
    assert exc_info.value.status_code == 422


# RN-2 CEPA-041: solicita_medidas=True sin detalle o sin fecha → rechazado
def test_coherencia_reca_rechaza_medidas_sin_detalle():
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_reca(
            solicita_medidas=True,
            detalle_medidas=None,
            fecha_medidas=None,
            verifica_medidas=False,
            fecha_verificacion=None,
        )
    assert exc_info.value.status_code == 422


def test_coherencia_reca_rechaza_medidas_sin_fecha():
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_reca(
            solicita_medidas=True,
            detalle_medidas="Ajuste ergonómico",
            fecha_medidas=None,
            verifica_medidas=False,
            fecha_verificacion=None,
        )
    assert exc_info.value.status_code == 422


# RN-2 CEPA-041: solicita_medidas=True con detalle y fecha → OK
def test_coherencia_reca_acepta_medidas_completas():
    validar_coherencia_reca(
        solicita_medidas=True,
        detalle_medidas="Ajuste ergonómico",
        fecha_medidas=datetime.date(2026, 3, 10),
        verifica_medidas=False,
        fecha_verificacion=None,
    )


# RN-1 CEPA-042: estado=total sin fecha_reintegro → rechazado (TC-042-03)
def test_coherencia_cierre_rechaza_total_sin_fecha():
    from app.domain.reintegro_enums import EstadoReintegro
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_cierre(
            estado=EstadoReintegro.TOTAL,
            fecha_reintegro=None,
            fecha_reca=datetime.date(2026, 4, 1),
            fecha_caso=None,
            alta_medica=True,
            alta_psicologica=False,
            tipo_alta="terapeutica",
        )
    assert exc_info.value.status_code == 422


# RN-2 CEPA-042: fecha_reintegro < fecha_reca → rechazado (TC-042-04)
def test_coherencia_cierre_rechaza_fecha_reintegro_anterior_a_reca():
    from app.domain.reintegro_enums import EstadoReintegro
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_cierre(
            estado=EstadoReintegro.TOTAL,
            fecha_reintegro=datetime.date(2026, 3, 15),
            fecha_reca=datetime.date(2026, 4, 1),
            fecha_caso=None,
            alta_medica=True,
            alta_psicologica=False,
            tipo_alta="terapeutica",
        )
    assert exc_info.value.status_code == 422


# RN-4 CEPA-042: reintegro total sin alta ni tipo_alta → rechazado (TC-042-05)
def test_coherencia_cierre_rechaza_total_sin_alta():
    from app.domain.reintegro_enums import EstadoReintegro
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_cierre(
            estado=EstadoReintegro.TOTAL,
            fecha_reintegro=datetime.date(2026, 5, 30),
            fecha_reca=datetime.date(2026, 4, 1),
            fecha_caso=None,
            alta_medica=False,
            alta_psicologica=False,
            tipo_alta=None,
        )
    assert exc_info.value.status_code == 422


# TC-042-01: reintegro total con todo completo → OK
def test_coherencia_cierre_acepta_total_completo():
    from app.domain.reintegro_enums import EstadoReintegro
    validar_coherencia_cierre(
        estado=EstadoReintegro.TOTAL,
        fecha_reintegro=datetime.date(2026, 5, 30),
        fecha_reca=datetime.date(2026, 4, 1),
        fecha_caso=None,
        alta_medica=True,
        alta_psicologica=False,
        tipo_alta="terapeutica",
    )


# TC-042-02: reintegro parcial sin fecha → permitido (caso abierto)
def test_coherencia_cierre_acepta_parcial_sin_fecha():
    from app.domain.reintegro_enums import EstadoReintegro
    validar_coherencia_cierre(
        estado=EstadoReintegro.PARCIAL,
        fecha_reintegro=None,
        fecha_reca=None,
        fecha_caso=None,
        alta_medica=False,
        alta_psicologica=False,
        tipo_alta=None,
    )


# ── Fix 1: RN-2 CEPA-042 — fecha_reintegro >= fecha_caso ─────────────────

# CEPA-042 RN-2: fecha_reintegro < fecha_caso → 422 (sin RECA presente)
def test_coherencia_cierre_rechaza_fecha_reintegro_anterior_a_fecha_caso():
    from app.domain.reintegro_enums import EstadoReintegro
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_cierre(
            estado=EstadoReintegro.TOTAL,
            fecha_reintegro=datetime.date(2026, 3, 10),
            fecha_reca=None,
            fecha_caso=datetime.date(2026, 4, 1),
            alta_medica=True,
            alta_psicologica=False,
            tipo_alta="terapeutica",
        )
    assert exc_info.value.status_code == 422
    assert "fecha_caso" in exc_info.value.detail


# fecha_reintegro >= fecha_caso (con RECA), todo OK
def test_coherencia_cierre_acepta_reintegro_posterior_a_fecha_caso():
    from app.domain.reintegro_enums import EstadoReintegro
    validar_coherencia_cierre(
        estado=EstadoReintegro.TOTAL,
        fecha_reintegro=datetime.date(2026, 5, 30),
        fecha_reca=datetime.date(2026, 4, 5),
        fecha_caso=datetime.date(2026, 3, 1),
        alta_medica=True,
        alta_psicologica=False,
        tipo_alta="terapeutica",
    )


# ── Fix 2: RN-4 CEPA-041 — verifica_medidas=True exige fecha_verificacion ──

# (a) verifica_medidas=True sin fecha_verificacion → 422
def test_coherencia_reca_rechaza_verifica_sin_fecha_verificacion():
    with pytest.raises(HTTPException) as exc_info:
        validar_coherencia_reca(
            solicita_medidas=False,
            detalle_medidas=None,
            fecha_medidas=None,
            verifica_medidas=True,
            fecha_verificacion=None,
        )
    assert exc_info.value.status_code == 422
    assert "fecha_verificacion" in exc_info.value.detail


# (b) verifica_medidas=True con fecha_verificacion → OK
def test_coherencia_reca_acepta_verifica_con_fecha_verificacion():
    validar_coherencia_reca(
        solicita_medidas=False,
        detalle_medidas=None,
        fecha_medidas=None,
        verifica_medidas=True,
        fecha_verificacion=datetime.date(2026, 4, 10),
    )
