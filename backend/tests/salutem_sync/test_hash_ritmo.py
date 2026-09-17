import pytest

from app.integrations.salutem.errors import SalutemAuthError, SalutemUnavailableError
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.services.salutem_sync import hash as modulo_hash
from app.services.salutem_sync.hash import hash_contenido
from app.services.salutem_sync.ritmo import Ritmo
from tests.salutem_falso import SalutemFalso


def test_el_falso_cumple_el_protocolo():
    assert isinstance(SalutemFalso(), SalutemClientProtocol)


def test_el_falso_resuelve_persona_con_rut_normalizado():
    falso = SalutemFalso()
    falso.agregar_persona(501, "12345678-5")

    resultado = falso.resolver_persona("123456785")

    assert resultado is not None
    assert resultado.salutem_id == 501


# ── hash ─────────────────────────────────────────────────────────────────────


def test_hash_no_depende_del_orden_de_las_claves():
    assert hash_contenido({"a": 1, "b": {"x": 1, "y": 2}}) == hash_contenido(
        {"b": {"y": 2, "x": 1}, "a": 1}
    )


def test_hash_cambia_con_el_contenido():
    h = hash_contenido({"anamnesis": "uno"})
    assert h != hash_contenido({"anamnesis": "dos"})
    assert len(h) == 64


def test_hash_ignora_campos_volatiles(monkeypatch):
    monkeypatch.setattr(modulo_hash, "CAMPOS_VOLATILES", frozenset({"tamanioBytes"}))
    assert hash_contenido({"a": 1, "tamanioBytes": 10}) == hash_contenido({"a": 1, "tamanioBytes": 99})


# ── ritmo ────────────────────────────────────────────────────────────────────


def test_espacia_las_llamadas_segun_la_frecuencia():
    dormidas: list[float] = []
    ritmo = Ritmo(2, dormir=dormidas.append, reloj=lambda: 10.0)

    ritmo.llamar(lambda: 1)
    ritmo.llamar(lambda: 1)

    assert dormidas == [0.5]
    assert ritmo.llamadas == 2


def test_reintenta_caidas_y_se_recupera():
    dormidas: list[float] = []
    intentos = {"n": 0}

    def inestable():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise SalutemUnavailableError("caída")
        return "ok"

    ritmo = Ritmo(0, dormir=dormidas.append)

    assert ritmo.llamar(inestable) == "ok"
    assert dormidas == [2.0, 4.0]
    assert ritmo.llamadas == 3


def test_tras_tres_reintentos_propaga_la_caida():
    dormidas: list[float] = []

    def caido():
        raise SalutemUnavailableError("caída")

    ritmo = Ritmo(0, dormir=dormidas.append)

    with pytest.raises(SalutemUnavailableError):
        ritmo.llamar(caido)
    assert dormidas == [2.0, 4.0, 8.0]
    assert ritmo.llamadas == 4


def test_no_reintenta_una_credencial_rechazada():
    def rechazo():
        raise SalutemAuthError("no")

    ritmo = Ritmo(0, dormir=lambda s: None)

    with pytest.raises(SalutemAuthError):
        ritmo.llamar(rechazo)
    assert ritmo.llamadas == 1
