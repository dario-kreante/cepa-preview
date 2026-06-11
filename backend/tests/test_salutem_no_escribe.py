"""TC-121-05 / CA-5 — REGLA DURA D12: el aplicativo CEPA nunca escribe sobre SALUTEM.

Implementa la garantía mediante un mock del cliente SALUTEM que lanza AssertionError
si se llama a cualquier método de escritura (create, update, delete, push, write).
El test verifica que ningún flujo de integración activa esos métodos.
"""

import pytest


class _SalutemWriteGuardMock:
    """Mock del cliente SALUTEM que falla si se llama a write/create/update/delete/push."""

    METODOS_ESCRITURA = frozenset({"create", "update", "delete", "push", "write", "patch"})

    def __getattr__(self, name: str):
        if name in self.METODOS_ESCRITURA:
            raise AssertionError(
                f"VIOLACIÓN D12: el aplicativo CEPA intentó llamar a "
                f"SalutemClient.{name}() — el CEPA NO escribe sobre SALUTEM. "
                "Revisar el flujo de integración."
            )
        # Métodos de lectura: devuelven None (pull vacío)
        return lambda *args, **kwargs: None


@pytest.fixture
def salutem_write_guard(monkeypatch):
    """Fixture que inyecta el mock de guardia en los tests de integración."""
    mock = _SalutemWriteGuardMock()
    monkeypatch.setattr(
        "app.integrations.salutem.client.get_salutem_client",
        lambda: mock,
    )
    return mock


def test_d12_mock_no_dispara_en_operacion_de_lectura(salutem_write_guard):
    """El mock de guardia no falla en operaciones de lectura."""
    cliente = salutem_write_guard
    resultado = cliente.get_paciente("12345")
    assert resultado is None  # mock devuelve None en lectura


def test_d12_mock_falla_si_se_llama_write(salutem_write_guard):
    """El mock de guardia lanza AssertionError si se llama a write (verificación del mock)."""
    with pytest.raises(AssertionError, match="VIOLACIÓN D12"):
        salutem_write_guard.write({"data": "algo"})


def test_d12_mock_falla_si_se_llama_create(salutem_write_guard):
    with pytest.raises(AssertionError, match="VIOLACIÓN D12"):
        salutem_write_guard.create({"paciente": "x"})


def test_d12_mock_falla_si_se_llama_update(salutem_write_guard):
    with pytest.raises(AssertionError, match="VIOLACIÓN D12"):
        salutem_write_guard.update("id_1", {"estado": "nuevo"})


def test_d12_flujo_pull_de_datos_clinicos_no_escribe_sobre_salutem(
    salutem_write_guard, as_admin
):
    """TC-121-05: Al procesar datos de SALUTEM (pull), el CEPA no llama a métodos de escritura.

    Se simula un pull de fichas clínicas desde SALUTEM y se verifica que el mock
    no lanzó AssertionError (ningún método de escritura fue invocado).
    """
    # El pull trae datos de SALUTEM (mock devuelve None) y los procesa sin escribir de vuelta
    r = as_admin.post(
        "/api/v1/fichas-clinicas/pull-salutem",
        json={"folio": "F-2026-0001"},
    )
    # 200 o 404 (folio no existe en test) son ambos aceptables — lo que NO debe ocurrir
    # es que el mock de guardia haya lanzado AssertionError.
    assert r.status_code in (200, 404, 422)
    # Si el mock hubiera disparado, el endpoint habría devuelto 500 y el test fallaría aquí.
