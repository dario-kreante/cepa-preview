from app.domain.enums_ept import (
    EstadoCumplimiento,
    EstadoEpt,
    FactorRiesgo,
    FactorRiesgoLegado,
)


def test_factor_riesgo_lista_del_area():
    """QA-003: 24 factores del área EPT, en el orden en que se muestran."""
    valores = [f.value for f in FactorRiesgo]
    assert len(valores) == 24
    assert len(set(valores)) == 24
    assert valores[0] == "sobrecarga"
    assert valores[-1] == "no_aplica"


def test_factor_riesgo_slugs_caben_en_la_columna():
    """La columna caso_ept.factor_riesgo es String(40)."""
    for f in [*FactorRiesgo, *FactorRiesgoLegado]:
        assert len(f.value) <= 40, f
        assert f.value.isascii() and f.value == f.value.lower(), f


def test_factor_riesgo_legado_no_se_solapa_con_el_nuevo():
    assert {f.value for f in FactorRiesgoLegado} == {
        "carga",
        "organizacion_trabajo",
        "factores_psicosociales",
        "violencia_laboral",
        "condiciones_ergonomicas",
        "otro",
    }
    assert not {f.value for f in FactorRiesgo} & {f.value for f in FactorRiesgoLegado}


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
