"""Cliente HTTP de SALUTEM — contrato verificado contra QA el 2026-09-07.

Los casos de este archivo replican comportamientos REALES observados en el
ambiente de pruebas, no lo que promete la documentación. En particular: la API
responde HTTP 200 incluso al rechazar la credencial, y `estado` llega como
booleano en éxito pero como string "false" en error.

Se usa httpx.MockTransport para no salir a la red: se ejerce el cliente de
verdad, solo se sustituye el transporte.
"""

import json
from datetime import date

import httpx
import pytest

from app.integrations.salutem.client import SalutemHttpClient
from app.integrations.salutem.errors import (
    SalutemAuthError,
    SalutemError,
    SalutemRequestError,
    SalutemUnavailableError,
)
from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol

BASE = "https://qa.salutem.cl/api/integraciones/salutem"
EMPRESA = "96"
KEY = "api-key-de-prueba"


def _cliente(handler) -> SalutemHttpClient:
    return SalutemHttpClient(
        base_url=BASE,
        empresa=EMPRESA,
        api_key=KEY,
        transport=httpx.MockTransport(handler),
    )


def _ok(respuesta):
    """Envoltorio de éxito tal como lo devuelve SALUTEM."""
    return httpx.Response(
        200, json={"estado": True, "api": "x", "parametros": {}, "respuesta": respuesta}
    )


def _falla(mensaje):
    """Error de SALUTEM: HTTP 200 y `estado` como string "false"."""
    return httpx.Response(200, json={"estado": "false", "mensaje": mensaje})


# ── Forma de la petición ──────────────────────────────────────────────────────


def test_la_peticion_va_como_get_con_body_json():
    """SALUTEM rechaza query params: los parámetros viajan en el cuerpo del GET."""
    visto = {}

    def handler(request: httpx.Request) -> httpx.Response:
        visto["metodo"] = request.method
        visto["url"] = str(request.url)
        visto["body"] = json.loads(request.content)
        return _ok({"demograficos": {"SALUTEM_ID": 1}})

    _cliente(handler).resolver_persona("11111111-1")

    assert visto["metodo"] == "GET"
    assert visto["body"]["identificacion"] == "11111111-1"
    assert visto["url"] == f"{BASE}/{EMPRESA}/personas"


def test_la_empresa_viaja_en_la_ruta_no_como_parametro():
    visto = {}

    def handler(request: httpx.Request) -> httpx.Response:
        visto["path"] = request.url.path
        return _ok([])

    _cliente(handler).listar_atenciones(42)

    assert visto["path"].startswith(f"/api/integraciones/salutem/{EMPRESA}/")
    assert "empresa" not in visto["path"].replace(f"/{EMPRESA}/", "/")


def test_la_credencial_va_en_el_header_api_key():
    visto = {}

    def handler(request: httpx.Request) -> httpx.Response:
        visto["api_key"] = request.headers.get("api-key")
        return _ok([])

    _cliente(handler).listar_atenciones(42)

    assert visto["api_key"] == KEY


def test_listar_citas_acota_la_ventana_a_un_solo_dia():
    """SALUTEM rechaza rangos que cruzan medianoche; el cliente nunca los arma."""
    visto = {}

    def handler(request: httpx.Request) -> httpx.Response:
        visto["body"] = json.loads(request.content)
        return _ok([])

    _cliente(handler).listar_citas(
        date(2025, 1, 22), EstadoCitaSalutem.ATENDIDO, TipoFechaCita.FECHA_CREACION
    )

    assert visto["body"]["fechaHoraInicio"] == "2025-01-22 00:00"
    assert visto["body"]["fechaHoraTermino"] == "2025-01-22 23:59"
    assert visto["body"]["citaEstadoId"] == "3"
    assert visto["body"]["tipo"] == 2


# ── Traducción de la respuesta ────────────────────────────────────────────────


def test_estado_string_false_con_http_200_se_traduce_a_error():
    """El fallo viene con HTTP 200: apoyarse en el código HTTP no sirve."""
    cliente = _cliente(lambda r: _falla("API_KEY_NO_VALIDA"))

    with pytest.raises(SalutemAuthError) as exc:
        cliente.resolver_persona("11111111-1")

    assert exc.value.codigo == "API_KEY_NO_VALIDA"


def test_empresa_sin_integracion_es_error_de_autenticacion():
    cliente = _cliente(lambda r: _falla("SIN_INTEGRACION_CONFIGURADA"))
    with pytest.raises(SalutemAuthError):
        cliente.listar_atenciones(42)


def test_parametro_invalido_es_error_de_peticion():
    cliente = _cliente(lambda r: _falla("ERROR_ESTADO_ID_NO_INGRESADO"))
    with pytest.raises(SalutemRequestError):
        cliente.listar_citas(date(2025, 1, 22), EstadoCitaSalutem.ATENDIDO)


def test_rut_mal_formado_es_error_de_peticion_no_ausencia():
    """Distinto de "la persona no existe": acá el dato que mandamos está mal."""
    cliente = _cliente(lambda r: _falla("ERROR_IDENTIFICACION_NO_VALIDA"))
    with pytest.raises(SalutemRequestError):
        cliente.resolver_persona("1-9")


def test_codigo_desconocido_no_se_traga_en_silencio():
    cliente = _cliente(lambda r: _falla("ERROR_MARCIANO"))
    with pytest.raises(SalutemError) as exc:
        cliente.listar_atenciones(42)
    assert exc.value.codigo == "ERROR_MARCIANO"


def test_persona_inexistente_devuelve_none_no_excepcion():
    """Que SALUTEM no tenga a la persona es un caso normal, no una falla."""
    cliente = _cliente(lambda r: _falla("ERROR_PERSONA_NO_EXISTE"))
    assert cliente.resolver_persona("22222222-2") is None


def test_cuerpo_ilegible_se_traduce_a_no_disponible():
    cliente = _cliente(lambda r: httpx.Response(200, text="<html>502</html>"))
    with pytest.raises(SalutemUnavailableError):
        cliente.listar_atenciones(42)


def test_falla_de_red_se_traduce_a_no_disponible():
    def handler(request):
        raise httpx.ConnectTimeout("timeout")

    with pytest.raises(SalutemUnavailableError):
        _cliente(handler).listar_atenciones(42)


# ── Mapeo a DTOs ──────────────────────────────────────────────────────────────


def test_resolver_persona_mapea_el_bloque_demograficos():
    payload = {
        "demograficos": {
            "SALUTEM_ID": 900001,
            "identificacion": "11111111-1",
            "tipoIdentificacion": "RUT",
            "nombres": "PACIENTE",
            "apellidos": "DE PRUEBA",
            "comuna": "Talca",
        }
    }
    persona = _cliente(lambda r: _ok(payload)).resolver_persona("11111111-1")

    assert persona is not None
    assert persona.salutem_id == 900001
    assert persona.tipo_identificacion == "RUT"
    assert persona.comuna == "Talca"
    assert persona.crudo == payload["demograficos"]


def test_listar_atenciones_mapea_la_hora_bajo_su_nombre_alternativo():
    """`/atencion` dice citaHorarioInicio donde `/cita` dice citaHoraInicio."""
    payload = [
        {
            "personaId": 900001,
            "citaId": 900777,
            "citaFecha": "2025-01-22",
            "citaHorarioInicio": "15:00:00",
            "estadoCitaNombre": "Atendido",
        }
    ]
    citas = _cliente(lambda r: _ok(payload)).listar_atenciones(900001)

    assert len(citas) == 1
    assert citas[0].cita_id == 900777
    assert citas[0].fecha == date(2025, 1, 22)
    assert citas[0].hora_inicio == "15:00:00"


def test_obtener_atencion_conserva_el_contenido_clinico_crudo():
    """El contenido varía por especialidad: se guarda tal cual, sin modelarlo."""
    payload = {
        "personaId": 900001,
        "citaId": 900777,
        "citaFecha": "2025-01-22",
        "diagnostico": {"registro": "algo", "diagnosticoPrincipal": 1},
        "refraccionAtencionDetalle": {"dpLejos": "69"},
    }
    atencion = _cliente(lambda r: _ok(payload)).obtener_atencion(900001, 900777)

    assert atencion is not None
    assert atencion.cita.cita_id == 900777
    assert atencion.contenido == payload


def test_atencion_inexistente_devuelve_none():
    cliente = _cliente(lambda r: _falla("ERROR_ATENCION_NO_EXISTE"))
    assert cliente.obtener_atencion(42, 999) is None


def test_respuesta_vacia_devuelve_lista_vacia():
    assert _cliente(lambda r: _ok([])).listar_atenciones(42) == []


# ── Conformidad con el contrato ───────────────────────────────────────────────


def test_el_cliente_http_satisface_el_protocolo():
    assert isinstance(_cliente(lambda r: _ok([])), SalutemClientProtocol)


def test_el_cliente_no_expone_metodos_de_escritura():
    """D12: el CEPA nunca escribe sobre SALUTEM."""
    cliente = _cliente(lambda r: _ok([]))
    for prohibido in ("create", "update", "delete", "push", "write", "patch"):
        assert not hasattr(cliente, prohibido), f"VIOLACIÓN D12: expone {prohibido}()"


# ── Fábrica: fail-closed ──────────────────────────────────────────────────────


@pytest.fixture
def settings_limpias(monkeypatch):
    """Aísla la configuración de SALUTEM entre tests."""
    from app.config import get_settings

    for var in ("SALUTEM_EMPRESA", "SALUTEM_API_KEY", "SALUTEM_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def test_sin_configuracion_la_fabrica_devuelve_el_stub(settings_limpias):
    """Fail-closed: sin credenciales no se sale a la red."""
    from app.integrations.salutem.client import SalutemStubClient, get_salutem_client

    assert isinstance(get_salutem_client(), SalutemStubClient)


def test_con_empresa_pero_sin_api_key_sigue_devolviendo_el_stub(settings_limpias):
    """Configuración a medias no habilita la integración."""
    from app.config import get_settings
    from app.integrations.salutem.client import SalutemStubClient, get_salutem_client

    settings_limpias.setenv("SALUTEM_EMPRESA", "96")
    get_settings.cache_clear()

    assert isinstance(get_salutem_client(), SalutemStubClient)


def test_con_configuracion_completa_la_fabrica_devuelve_el_cliente_http(
    settings_limpias,
):
    from app.config import get_settings
    from app.integrations.salutem.client import get_salutem_client

    settings_limpias.setenv("SALUTEM_EMPRESA", "96")
    settings_limpias.setenv("SALUTEM_API_KEY", "una-key")
    get_settings.cache_clear()

    cliente = get_salutem_client()
    assert isinstance(cliente, SalutemHttpClient)
    assert cliente._empresa == "96"


# ── obtener_persona (sync fase 1) ─────────────────────────────────────────────


def test_obtener_persona_envia_persona_id_en_el_cuerpo():
    vistos = []

    def handler(request):
        vistos.append((request.url.path, json.loads(request.content)))
        return _ok(
            {"demograficos": {"SALUTEM_ID": 338735, "identificacion": "11168636-k", "nombres": "ALEX"}}
        )

    persona = _cliente(handler).obtener_persona(338735)

    assert persona is not None
    assert persona.salutem_id == 338735
    assert vistos == [
        (
            f"/api/integraciones/salutem/{EMPRESA}/personas",
            {"persona_id": 338735, "agrupacion": "demograficos"},
        )
    ]


def test_obtener_persona_inexistente_devuelve_none():
    cliente = _cliente(lambda request: _falla("ERROR_PERSONA_NO_EXISTE"))
    assert cliente.obtener_persona(1) is None


def test_stub_obtener_persona_devuelve_none():
    from app.integrations.salutem.client import SalutemStubClient

    assert SalutemStubClient().obtener_persona(1) is None
