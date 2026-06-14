from app.domain.enums_licencia import EstadoEnvioISL, OrigenLicencia, TipoLicencia, TipoReposo


def test_tipo_licencia_catalogo_exacto():
    """RN-3 CEPA-070: solo valores {1, 5, 6}."""
    valores = {t.value for t in TipoLicencia}
    assert valores == {"1", "5", "6"}


def test_tipo_reposo_catalogo_exacto():
    """RN-3 CEPA-070: solo {total, parcial}."""
    valores = {t.value for t in TipoReposo}
    assert valores == {"total", "parcial"}


def test_estado_envio_isl_catalogo_exacto():
    """RN-2 CEPA-073: {pendiente, enviado, rechazado}."""
    valores = {e.value for e in EstadoEnvioISL}
    assert valores == {"pendiente", "enviado", "rechazado"}


def test_origen_licencia_catalogo_exacto():
    """RN-4 CEPA-073: {sistema, extra_sistema}."""
    valores = {o.value for o in OrigenLicencia}
    assert valores == {"sistema", "extra_sistema"}


def test_todos_los_enums_son_str():
    for klass in (TipoLicencia, TipoReposo, EstadoEnvioISL, OrigenLicencia):
        for miembro in klass:
            assert isinstance(miembro.value, str), f"{klass.__name__}.{miembro.name} no es str"
