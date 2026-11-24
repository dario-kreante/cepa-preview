"""Clasificación de fármacos por convenio (QA-010 / QA-013): reglas con catálogos pequeños."""

from app.domain.farmacos_convenio import (
    Clasificador,
    ItemCanasta,
    ItemExternalizado,
    coincide,
    tokens,
)

CANASTA = [
    ItemCanasta("3073", "ALPRAZOLAM 0.5MG. CAJA 30 COMP.", "ALPRAZOLAM", "GENERICO"),
    ItemCanasta("20205", "DEPRAX 50MG. CAJA 30 COMP. REC", "SERTRALINA CLORHIDRATO", "DEPRAX"),
    ItemCanasta("22024", "MELATONINA 3MG.30CAP.", "MELATONINA", "FARMACIAS AHUMADA"),
    ItemCanasta("76440", "BUTRINO 150 MG CAJA 30 COMP.REC.L.P", "ANFEBUTAMONA (BUPROPION)", "BUTRIN"),
]
LISTA = [
    ItemExternalizado("CIRCALIFE MELATONINA 3MG", True, False),
    ItemExternalizado("MELATONINA 3 MG 60 CAPS", True, False),
    ItemExternalizado("ESCITALOPRAM 10MG. CAJA 3", False, True),  # truncada a 25
]
K = Clasificador(CANASTA, LISTA)


def test_tokens_normaliza_tildes_comas_y_unidades_pegadas():
    assert tokens("Alprazolam 0,5MG. Caja") == ["alprazolam", "0.5", "mg", "caja"]
    assert tokens("Clonazepám 2mg") == ["clonazepam", "2", "mg"]


def test_coincide_por_prefijo_de_palabras_y_no_por_caracteres():
    ref = tokens("DEPRAX 50MG. CAJA 30")
    assert coincide(tokens("Deprax 50 mg"), ref)
    assert not coincide(tokens("Deprax 5"), ref)  # 5 ≠ 50
    assert coincide(tokens("Escitalopram 10 mg caja 30"), tokens("ESCITALOPRAM 10MG. CAJA 3"), ref_truncada=True)
    assert not coincide(tokens("Escitalopram 10 mg caja 30"), tokens("ESCITALOPRAM 10MG. CAJA 3"))


def test_codigo_sap_en_la_canasta():
    r = K.clasificar("SAP 3073")
    assert (r.clasificacion, r.codigo_sap) == ("Convenio 002", "3073")


def test_un_numero_seguido_de_unidad_es_dosis_y_no_codigo_sap():
    r = K.clasificar("Paracetamol 3073 mg")
    assert r.clasificacion == "Fuera de convenio"


def test_nombre_y_presentacion_de_la_canasta():
    r = K.clasificar("Alprazolam 0,5 mg")
    assert (r.clasificacion, r.codigo_sap) == ("Convenio 002", "3073")
    assert K.clasificar("Deprax 50mg").clasificacion == "Convenio 002"


def test_lista_externalizado_convenio_001_y_002():
    assert K.clasificar("Circalife melatonina 3 mg").clasificacion == "Convenio 001"
    r = K.clasificar("Escitalopram 10 mg caja 30")
    assert (r.clasificacion, r.codigo_sap) == ("Convenio 002", None)


def test_varias_opciones_de_distinto_convenio_es_revisar():
    r = K.clasificar("Melatonina 3 mg")  # canasta 002 y lista 001
    assert r.clasificacion == "REVISAR"
    assert "distintos convenios" in r.detalle
    assert set(r.coincidencias) == {"MELATONINA 3MG.30CAP.", "MELATONINA 3 MG 60 CAPS"}


def test_misma_marca_otra_dosis_es_revisar():
    r = K.clasificar("Deprax 100 mg")
    assert r.clasificacion == "REVISAR"
    assert "DEPRAX" in r.detalle


def test_solo_principio_activo_es_revisar():
    r = K.clasificar("Bupropión 300 mg")
    assert r.clasificacion == "REVISAR"
    assert "principio activo" in r.detalle


def test_fuera_de_convenio_y_texto_vacio():
    assert K.clasificar("Paracetamol 500 mg").clasificacion == "Fuera de convenio"
    assert K.clasificar("   ").clasificacion == "REVISAR"
