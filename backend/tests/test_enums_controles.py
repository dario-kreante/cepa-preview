from app.domain.enums_controles import EstadoReca, TipoLicencia, TipoReposo


def test_tipo_reposo_valores():
    assert {t.value for t in TipoReposo} == {"total", "parcial"}


def test_tipo_licencia_incluye_tipos_basicos():
    valores = {t.value for t in TipoLicencia}
    # al menos tipo 1, 5 y 6 (§7.7.1 / CEPA-062 RN-4)
    assert "1" in valores
    assert "5" in valores
    assert "6" in valores
    # licencia extra-sistema (D7)
    assert "extra_sistema" in valores


def test_estado_reca_valores():
    assert {e.value for e in EstadoReca} == {
        "pendiente",
        "aprobado",
        "rechazado",
        "en_proceso",
        "no_aplica",
    }
