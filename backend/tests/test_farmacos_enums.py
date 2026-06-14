from app.domain.enums import EstadoFarmacologico, FrecuenciaFarmaco


def test_estados_farmacologicos():
    valores = {e.value for e in EstadoFarmacologico}
    assert valores == {"activo", "suspendido", "completado", "pendiente"}


def test_frecuencias_farmaco():
    valores = {f.value for f in FrecuenciaFarmaco}
    assert "c/24h" in valores
    assert "c/12h" in valores
    assert "c/8h" in valores
    assert "c/6h" in valores
    assert "semanal" in valores
    assert "otro" in valores
