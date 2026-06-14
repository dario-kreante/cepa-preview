from app.domain.enums_ept import EstadoCumplimiento, EstadoEpt, FactorRiesgo


def test_factor_riesgo_lista_cerrada():
    valores = {f.value for f in FactorRiesgo}
    assert "carga" in valores
    assert "organizacion_trabajo" in valores
    assert "factores_psicosociales" in valores
    assert len(valores) >= 3


def test_estado_ept():
    assert {e.value for e in EstadoEpt} == {
        "abierto",
        "no_corresponde",
        "cerrado",
    }


def test_estado_cumplimiento():
    assert {e.value for e in EstadoCumplimiento} == {
        "en_plazo",
        "por_vencer",
        "vencido",
        "cumplido",
    }
