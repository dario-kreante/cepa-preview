from app.domain.enums import (
    EstadoCaso,
    EstadoConsentimiento,
    EstadoEvaluacion,
    Sexo,
    TipoAlta,
    TipoDerivacion,
    TipoIngreso,
)


def test_tipos_de_derivacion_son_la_lista_cerrada_v4_d4():
    valores = {d.value for d in TipoDerivacion}
    assert valores == {
        "DIEP",
        "DIAT",
        "PAPT a flujo AT",
        "Reingreso FUMP",
        "Reingreso SUSESO",
        "Convenio U.Clinica",
        "Proyecto",
        "Particular",
        "PAPT",
    }
    # El antiguo convenio SOCORRO ya no es válido (D4)
    assert "SOCORRO" not in valores


def test_estados_de_caso():
    assert {e.value for e in EstadoCaso} == {"activo", "cerrado", "derivado"}


def test_tipos_de_alta_v4_d6():
    assert {t.value for t in TipoAlta} == {
        "terapeutica",
        "medica",
        "psicologica",
        "abandono",
        "derivacion",
    }


def test_estados_de_evaluacion():
    assert {e.value for e in EstadoEvaluacion} == {"realizada", "pendiente", "no_aplica"}


def test_estado_consentimiento():
    assert {e.value for e in EstadoConsentimiento} == {"firmado", "pendiente"}


def test_sexo_y_tipo_ingreso_existen():
    assert "F" in {s.value for s in Sexo}
    assert "M" in {s.value for s in Sexo}
    assert len(list(TipoIngreso)) >= 1
