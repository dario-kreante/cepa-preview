"""Qué nota de SALUTEM es un addendum (QA-008): una sola regla, en app.domain.addendum."""

import pytest

from app.domain.addendum import es_addendum


@pytest.mark.parametrize(
    "texto",
    ["Prueba addendum. Se corrige", "ADENDUM fecha 04-11", "Adenda: reposo", "ÁDDENDA", "addenda al control"],
)
def test_menciona_addendum(texto):
    assert es_addendum(texto) is True


@pytest.mark.parametrize("texto", ["Paciente llega tarde", "", None, "adenoma"])
def test_no_es_addendum(texto):
    assert es_addendum(texto) is False
