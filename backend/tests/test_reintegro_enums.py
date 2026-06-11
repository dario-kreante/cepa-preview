from app.domain.reintegro_enums import (
    EstadoReintegro,
    TipoAlta as TipoAltaReintegro,
    TipoReca,
)


def test_estado_reintegro_lista_cerrada():
    valores = {e.value for e in EstadoReintegro}
    assert valores == {"pendiente", "parcial", "total"}


def test_tipo_reca_existe():
    # lista cerrada; los valores vienen del spec (pendiente de catálogo definitivo)
    valores = {t.value for t in TipoReca}
    assert "AT" in valores    # Accidente del Trabajo
    assert "EP" in valores    # Enfermedad Profesional


def test_tipo_alta_reintegro():
    valores = {t.value for t in TipoAltaReintegro}
    assert "terapeutica" in valores
    assert "medica" in valores
    assert "psicologica" in valores
    assert "abandono" in valores
    assert "derivacion" in valores


# Fix 3: TipoAlta en reintegro_enums debe ser el mismo objeto que app.domain.enums.TipoAlta
def test_tipo_alta_reintegro_es_reexport_de_enums():
    from app.domain.enums import TipoAlta as TipoAltaCore
    assert TipoAltaReintegro is TipoAltaCore
