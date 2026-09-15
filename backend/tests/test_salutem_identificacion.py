"""El RUT viaja a SALUTEM con guion, aunque el CEPA lo guarde sin él.

La forma canónica que persiste el CEPA es `<cuerpo><DV>` (app/util/rut.py), pero
SALUTEM rechaza ese formato con ERROR_IDENTIFICACION_NO_VALIDA: exige
`<cuerpo>-<DV>`. Visto en la VM de UTalca el 15-09-2026, primero con un paciente
real de Oracle y después con el paciente del sandbox (RUT guardado `162158066`).
"""

import json

import httpx
import pytest

from app.integrations.salutem.client import SalutemHttpClient


def _cliente_que_captura(visto: dict) -> SalutemHttpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        visto["body"] = json.loads(request.content)
        return httpx.Response(200, json={"estado": "false", "mensaje": "ERROR_PERSONA_NO_EXISTE"})

    return SalutemHttpClient(
        base_url="https://salutem.test/api",
        empresa="96",
        api_key="k",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    "rut_cepa",
    [
        "162158066",  # forma canónica que guarda el CEPA
        "16.215.806-6",  # con puntos y guion
        "16215806-6",  # ya en el formato de SALUTEM
    ],
)
def test_resolver_persona_envia_el_rut_con_guion(rut_cepa):
    visto: dict = {}
    _cliente_que_captura(visto).resolver_persona(rut_cepa)
    assert visto["body"]["identificacion"] == "16215806-6"


def test_rut_con_dv_k_conserva_la_k_en_mayuscula():
    visto: dict = {}
    _cliente_que_captura(visto).resolver_persona("1000005k")
    assert visto["body"]["identificacion"] == "1000005-K"


def test_rut_invalido_se_envia_tal_cual_para_que_salutem_lo_rechace():
    """No se inventa un RUT: si no valida, SALUTEM responde y el CEPA da 422."""
    visto: dict = {}
    _cliente_que_captura(visto).resolver_persona("12345678-0")
    assert visto["body"]["identificacion"] == "12345678-0"
