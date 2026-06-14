import pytest

from app.util.rut import RutInvalidoError, formatear_rut, normalizar_rut, validar_rut


def test_rut_valido_con_dv_numerico():
    assert validar_rut("12.345.678-5") is True


def test_rut_valido_con_dv_k():
    # 1.000.005-K es un RUT con dígito verificador K
    assert validar_rut("1.000.005-k") is True
    assert validar_rut("1000005K") is True


def test_rut_invalido_dv_erroneo():
    assert validar_rut("12.345.678-0") is False


def test_rut_invalido_no_numerico():
    assert validar_rut("abc-1") is False
    assert validar_rut("") is False
    assert validar_rut("-5") is False


def test_normalizar_quita_puntos_guion_y_pone_dv_mayuscula():
    assert normalizar_rut("12.345.678-5") == "123456785"
    assert normalizar_rut("1.000.005-k") == "1000005K"


def test_normalizar_rechaza_rut_invalido():
    with pytest.raises(RutInvalidoError):
        normalizar_rut("12.345.678-0")


def test_formatear_agrega_puntos_y_guion():
    assert formatear_rut("123456785") == "12.345.678-5"
    assert formatear_rut("1000005K") == "1.000.005-K"
