from app.domain.reintegro_enums import (
    EstadoReintegro,
    TipoAlta as TipoAltaReintegro,
    TipoReca,
)


def test_estado_reintegro_lista_cerrada():
    valores = {e.value for e in EstadoReintegro}
    assert valores == {"pendiente", "parcial", "total"}


def test_tipo_reca_es_el_catalogo_d20():
    # Decisiones v5 D20: EP · EC · AT · AC · NPE · No aplica
    valores = {t.value for t in TipoReca}
    assert valores == {"EP", "EC", "AT", "AC", "NPE", "no_aplica"}


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
