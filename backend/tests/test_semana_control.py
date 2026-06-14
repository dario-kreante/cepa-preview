import pytest
from datetime import date

from app.services.semana_control import (
    FechaControlInvalidaError,
    calcular_semana_control,
)


# TC-060-01: fecha_ingreso=2026-01-05, fecha_control=2026-02-02 → semana 5
def test_tc_060_01_semana_5():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 1, 5),
        fecha_control=date(2026, 2, 2),
    )
    assert semana == 5


# TC-060-02: fecha_ingreso=2026-03-02, fecha_control=2026-03-10 → semana 2
def test_tc_060_02_semana_2():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 3, 2),
        fecha_control=date(2026, 3, 10),
    )
    assert semana == 2


# TC-060-05 (borde): mismo día → semana 1
def test_tc_060_05_mismo_dia_semana_1():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 4, 1),
        fecha_control=date(2026, 4, 1),
    )
    assert semana == 1


# Borde: día siguiente (1 día de diferencia) → semana 1
def test_un_dia_despues_es_semana_1():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 2),
    )
    assert semana == 1


# Borde: exactamente 7 días → semana 2 (la semana 1 cubre días 0-6)
def test_siete_dias_exactos_es_semana_2():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 8),
    )
    assert semana == 2


# Borde: 6 días → semana 1 (último día de la semana 1)
def test_seis_dias_es_semana_1():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 7),
    )
    assert semana == 1


# Borde: 14 días exactos → semana 3
def test_catorce_dias_exactos_es_semana_3():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 6, 1),
        fecha_control=date(2026, 6, 15),
    )
    assert semana == 3


# RN-4: fecha_control anterior a fecha_ingreso → error
def test_fecha_control_anterior_a_ingreso_lanza_error():
    with pytest.raises(FechaControlInvalidaError, match="anterior"):
        calcular_semana_control(
            fecha_ingreso=date(2026, 6, 10),
            fecha_control=date(2026, 6, 9),
        )


# RN-4: un año completo después
def test_un_anio_de_diferencia():
    semana = calcular_semana_control(
        fecha_ingreso=date(2026, 1, 1),
        fecha_control=date(2027, 1, 1),  # 365 días
    )
    # 365 // 7 + 1 = 52 + 1 = 53
    assert semana == 53
