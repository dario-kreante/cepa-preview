"""Extractor de fármacos y campos estructurados de SALUTEM (textos del ambiente de pruebas)."""

import pytest

from app.domain.enums import FrecuenciaFarmaco as F
from app.integrations.salutem.campos import antecedente, tramo_gaf, valor_campo
from app.integrations.salutem.farmacos import AVISO_SIN_FRECUENCIA, AVISO_SOS, extraer_farmacos


def _una(texto):
    [m] = extraer_farmacos(texto)
    return (m.medicamento, m.dosis, m.frecuencia)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Sertralina 50 mg 1 al dia", ("Sertralina", "50 mg", F.C24H)),
        ("Sertralina 100 mg 1 comp cada 24 horas", ("Sertralina", "100 mg", F.C24H)),
        ("Clotiazepam 5 mg 1por dia", ("Clotiazepam", "5 mg", F.C24H)),
        ("quetiapina 25mg cada 12 hrs", ("Quetiapina", "25 mg", F.C12H)),
        ("Escitalopram 10 mg 2 veces al día", ("Escitalopram", "10 mg", F.C12H)),
        ("Zopiclona 7,5 mg en la noche", ("Zopiclona", "7.5 mg", F.C24H)),
        ("Clotiazepam 10 mg SOS", ("Clotiazepam", "10 mg SOS", F.OTRO)),
    ],
)
def test_estructura_medicamento_dosis_y_frecuencia(texto, esperado):
    assert _una(texto) == esperado


def test_una_receta_con_varias_lineas_da_un_farmaco_por_linea():
    menciones = extraer_farmacos("Clotiazepam 5 mg SOS\r\n\r\nSertralina 100 mg 1 al día")
    assert [(m.medicamento, m.dosis, m.frecuencia) for m in menciones] == [
        ("Clotiazepam", "5 mg SOS", F.OTRO),
        ("Sertralina", "100 mg", F.C24H),
    ]
    assert menciones[0].avisos == [AVISO_SOS]
    assert menciones[1].avisos == []


def test_lee_recetas_en_html():
    menciones = extraer_farmacos("<p>1. Sertralina 50 mg 1 al día<br>2. Clonazepam 0,5 mg noche</p>")
    assert [m.medicamento for m in menciones] == ["Sertralina", "Clonazepam"]


def test_sin_frecuencia_reconocible_queda_otro_con_aviso():
    [m] = extraer_farmacos("Pregabalina 75 mg")
    assert m.frecuencia == F.OTRO
    assert m.avisos == [AVISO_SIN_FRECUENCIA]


@pytest.mark.parametrize("basura", ["fsdfsdff", "561651", "", None, "Control en 1 mes", "5 mg"])
def test_descarta_lo_que_no_es_un_medicamento_con_dosis(basura):
    assert extraer_farmacos(basura) == []


@pytest.mark.parametrize(
    ("registro", "esperado"),
    [
        ({"2": "Total"}, "Total"),
        (["Alta médica"], "Alta médica"),
        ("{'1': '51-60'}", "51-60"),
        ("['Enfermedad común']", "Enfermedad común"),
        ("texto <b>libre</b>", "texto libre"),
        ("", None),
        (None, None),
    ],
)
def test_valor_campo_normaliza_las_formas_de_salutem(registro, esperado):
    assert valor_campo(registro) == esperado


def test_antecedente_busca_por_nombre():
    contenido = {"antecedentes": [{"agrupacion": "", "nombre": "GAF", "registro": {"1": "41-50"}}]}
    assert antecedente(contenido, "GAF") == "41-50"
    assert antecedente(contenido, "Tipo de reposo") is None


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("51-60", "51-60"),
        (" 41 - 50 ", "41-50"),
        ("91–100", "91-100"),
        ("50", None),
        ("70-60", None),
        (None, None),
    ],
)
def test_tramo_gaf(valor, esperado):
    assert tramo_gaf(valor) == esperado
