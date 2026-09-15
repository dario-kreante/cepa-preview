"""Clientes SALUTEM: el stub inerte y el cliente HTTP real.

La fábrica elige entre ambos según configuración, de modo que los llamadores
nunca sepan cuál está activo.

REGLA D12: ningún cliente de este módulo expone métodos de escritura.
"""

from datetime import date
from typing import Any

import httpx

from app.config import get_settings
from app.integrations.salutem.errors import (
    CODIGOS_NO_ENCONTRADO,
    SalutemUnavailableError,
    error_desde_codigo,
)
from app.integrations.salutem.models import (
    AtencionSalutem,
    CitaSalutem,
    EstadoCitaSalutem,
    PersonaSalutem,
    TipoFechaCita,
)
from app.integrations.salutem.protocol import SalutemClientProtocol


class SalutemStubClient:
    """Cliente inerte: no hay datos, no hay red.

    Es el comportamiento por defecto mientras la integración no esté
    configurada, y el que usan los tests que no simulan SALUTEM. Devolver
    vacío (en vez de fallar) mantiene los flujos de pull operativos: un
    ingreso sin datos en SALUTEM es un caso normal, no un error.
    """

    def resolver_persona(self, rut: str) -> PersonaSalutem | None:  # noqa: ARG002
        return None

    def listar_atenciones(self, salutem_id: int) -> list[CitaSalutem]:  # noqa: ARG002
        return []

    def obtener_atencion(  # noqa: ARG002
        self, salutem_id: int, cita_id: int
    ) -> AtencionSalutem | None:
        return None

    def listar_citas(  # noqa: ARG002
        self,
        dia: date,
        estado: EstadoCitaSalutem,
        por: TipoFechaCita = TipoFechaCita.FECHA_CITA,
    ) -> list[CitaSalutem]:
        return []


class SalutemHttpClient:
    """Cliente HTTP contra la API de integraciones de SALUTEM.

    Tres rarezas de la API que este cliente absorbe para que el dominio no las
    vea, todas verificadas contra QA:

    1. Los GET llevan los parámetros en el CUERPO. Con query params la API
       responde ERROR_PETICION_NO_SOPORTADA.
    2. El HTTP es siempre 200, incluso al rechazar la credencial. El resultado
       real está en `estado`, que además llega como booleano en éxito y como
       string "false" en error.
    3. "No existe" no es una falla: se traduce a None / lista vacía.
    """

    def __init__(
        self,
        base_url: str,
        empresa: str,
        api_key: str,
        timeout_s: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._empresa = empresa
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._transport = transport

    def _get(self, ruta: str, payload: dict[str, Any]) -> Any:
        """Ejecuta un GET con cuerpo y devuelve `respuesta`, o None si no existe."""
        url = f"{self._base_url}/{self._empresa}/{ruta}"
        try:
            with httpx.Client(
                transport=self._transport, timeout=self._timeout_s
            ) as http:
                r = http.request(
                    "GET", url, json=payload, headers={"api-key": self._api_key}
                )
        except httpx.HTTPError as e:
            raise SalutemUnavailableError(f"SALUTEM no respondió: {e}") from e

        try:
            cuerpo = r.json()
        except ValueError as e:
            raise SalutemUnavailableError(
                f"SALUTEM devolvió un cuerpo ilegible (HTTP {r.status_code})"
            ) from e

        # `estado` es True (bool) en éxito y "false" (str) en error: normalizar.
        estado = cuerpo.get("estado")
        if not (estado is True or str(estado).lower() == "true"):
            codigo = cuerpo.get("mensaje") or "DESCONOCIDO"
            if codigo in CODIGOS_NO_ENCONTRADO:
                return None
            raise error_desde_codigo(codigo)

        return cuerpo.get("respuesta")

    def resolver_persona(self, rut: str) -> PersonaSalutem | None:
        r = self._get(
            "personas", {"identificacion": rut, "agrupacion": "demograficos"}
        )
        if not r or "demograficos" not in r:
            return None
        return PersonaSalutem.desde_api(r["demograficos"])

    def listar_atenciones(self, salutem_id: int) -> list[CitaSalutem]:
        r = self._get("atencion", {"persona_id": salutem_id})
        return [CitaSalutem.desde_api(x) for x in (r or [])]

    def obtener_atencion(
        self, salutem_id: int, cita_id: int
    ) -> AtencionSalutem | None:
        r = self._get("atencion", {"persona_id": salutem_id, "cita_id": cita_id})
        return AtencionSalutem.desde_api(r) if r else None

    def listar_citas(
        self,
        dia: date,
        estado: EstadoCitaSalutem,
        por: TipoFechaCita = TipoFechaCita.FECHA_CITA,
    ) -> list[CitaSalutem]:
        # La ventana no cruza medianoche: SALUTEM rechaza rangos multi-día.
        r = self._get(
            "cita",
            {
                "fechaHoraInicio": f"{dia.isoformat()} 00:00",
                "fechaHoraTermino": f"{dia.isoformat()} 23:59",
                "citaEstadoId": str(int(estado)),
                "tipo": int(por),
            },
        )
        return [CitaSalutem.desde_api(x) for x in (r or [])]


_STUB_CLIENT: SalutemClientProtocol = SalutemStubClient()


def get_salutem_client() -> SalutemClientProtocol:
    """Fábrica del cliente SALUTEM. Inyectable en tests con monkeypatch.

    Si `salutem_empresa` o `salutem_api_key` están vacíos, la integración está
    deshabilitada y se devuelve el stub: fail-closed, sin credenciales no se
    sale a la red. Una configuración a medias tampoco habilita nada.
    """
    settings = get_settings()
    if not (settings.salutem_empresa and settings.salutem_api_key):
        return _STUB_CLIENT
    return SalutemHttpClient(
        base_url=settings.salutem_base_url,
        empresa=settings.salutem_empresa,
        api_key=settings.salutem_api_key,
        timeout_s=settings.salutem_timeout_s,
    )
