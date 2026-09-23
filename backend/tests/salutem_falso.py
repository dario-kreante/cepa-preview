"""SALUTEM en memoria para probar el sync sin red.

Implementa `SalutemClientProtocol` con los mismos formatos crudos que la API
real (claves camelCase, fechas como string) y registra cada llamada.
"""

from collections.abc import Callable
from datetime import date

from app.integrations.salutem.errors import (
    SalutemAuthError,
    SalutemError,
    SalutemRequestError,
    SalutemUnavailableError,
)
from app.integrations.salutem.models import (
    AtencionSalutem,
    CitaSalutem,
    EstadoCitaSalutem,
    PersonaSalutem,
    TipoFechaCita,
)
from app.util.rut import RutInvalidoError, normalizar_rut


def _normalizar_o_tal_cual(rut: str) -> str:
    """Normaliza el RUT como hace el cliente real; si no valida, lo deja tal cual."""
    try:
        return normalizar_rut(rut)
    except RutInvalidoError:
        return rut


def _error_no_catalogado() -> SalutemError:
    return SalutemError("no catalogado", codigo="ERROR_RARO")


class SalutemFalso:
    def __init__(self) -> None:
        self.personas: dict[int, dict] = {}
        self.citas: dict[int, dict] = {}
        self.atenciones: dict[int, dict] = {}
        self.llamadas: list[tuple] = []
        # (dia, estado) que SALUTEM rechaza con SalutemRequestError.
        self.dias_con_error: set[tuple[date, int]] = set()
        # Si se define, `dias_con_error` levanta este error en vez de SalutemRequestError.
        self.error_de_listado: SalutemError | None = None
        # Registros puntuales que SALUTEM rechaza con un código no catalogado.
        self.citas_con_error: set[int] = set()
        self.personas_con_error: set[int] = set()
        # Cuántas de las próximas llamadas fallan con SalutemUnavailableError.
        self.caidas_pendientes = 0
        # Días en los que SALUTEM está caído: cada llamada de ese día falla (p.ej. HTTP 504).
        self.dias_caidos: set[date] = set()
        self.personas_caidas: set[int] = set()
        self.credencial_rechazada = False
        # Hook de prueba: se invoca al empezar `listar_citas`, después de `_registrar`.
        self.antes_de_listar: Callable[[date, int], None] | None = None

    # ── Carga de datos ─────────────────────────────────────────────────────
    def agregar_persona(self, salutem_id: int, rut: str = "12345678-5", **extra) -> None:
        self.personas[salutem_id] = {
            "SALUTEM_ID": salutem_id,
            "identificacion": rut,
            "tipoIdentificacion": "RUT",
            **extra,
        }

    def agregar_cita(
        self,
        cita_id: int,
        persona_id: int,
        fecha: date,
        estado: int = EstadoCitaSalutem.ATENDIDO,
        creada: str | None = None,
        **extra,
    ) -> None:
        self.citas[cita_id] = {
            "personaId": persona_id,
            "citaId": cita_id,
            "citaFecha": fecha.isoformat(),
            "citaFechaCreacion": creada or f"{fecha.isoformat()} 08:00",
            "estadoCitaId": int(estado),
            **extra,
        }

    def agregar_atencion(self, cita_id: int, **contenido) -> None:
        self.atenciones[cita_id] = {"anamnesis": "", **contenido}

    # ── Protocolo ──────────────────────────────────────────────────────────
    def _registrar(self, *llamada) -> None:
        self.llamadas.append(llamada)
        if self.credencial_rechazada:
            raise SalutemAuthError("credencial rechazada", codigo="API_KEY_NO_VALIDA")
        if self.caidas_pendientes > 0:
            self.caidas_pendientes -= 1
            raise SalutemUnavailableError("caída simulada")

    def resolver_persona(self, rut: str) -> PersonaSalutem | None:
        self._registrar("resolver_persona", rut)
        buscado = _normalizar_o_tal_cual(rut)
        for p in self.personas.values():
            if _normalizar_o_tal_cual(p["identificacion"]) == buscado:
                return PersonaSalutem.desde_api(p)
        return None

    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:
        self._registrar("obtener_persona", salutem_id)
        if salutem_id in self.personas_con_error:
            raise _error_no_catalogado()
        p = self.personas.get(salutem_id)
        return PersonaSalutem.desde_api(p) if p else None

    def listar_atenciones(self, salutem_id: int) -> list[CitaSalutem]:
        self._registrar("listar_atenciones", salutem_id)
        if salutem_id in self.personas_caidas:
            raise SalutemUnavailableError("SALUTEM devolvió un cuerpo ilegible (HTTP 504)")
        return [
            CitaSalutem.desde_api(cita)
            for cita_id in self.atenciones
            if (cita := self.citas.get(cita_id)) is not None
            and cita["personaId"] == salutem_id
        ]

    def obtener_atencion(self, salutem_id: int, cita_id: int) -> AtencionSalutem | None:
        self._registrar("obtener_atencion", salutem_id, cita_id)
        if cita_id in self.citas_con_error:
            raise _error_no_catalogado()
        cita = self.citas.get(cita_id)
        if cita_id not in self.atenciones or cita is None or cita["personaId"] != salutem_id:
            return None
        return AtencionSalutem.desde_api({**cita, **self.atenciones[cita_id]})

    def listar_citas(
        self,
        dia: date,
        estado: EstadoCitaSalutem,
        por: TipoFechaCita = TipoFechaCita.FECHA_CITA,
    ) -> list[CitaSalutem]:
        self._registrar("listar_citas", dia, int(estado), int(por))
        if self.antes_de_listar is not None:
            self.antes_de_listar(dia, int(estado))
        if dia in self.dias_caidos:
            raise SalutemUnavailableError("SALUTEM devolvió un cuerpo ilegible (HTTP 504)")
        if (dia, int(estado)) in self.dias_con_error:
            if self.error_de_listado is not None:
                raise self.error_de_listado
            raise SalutemRequestError("rechazada", codigo="ERROR_INTERVALO_SUPERADO")
        campo = "citaFecha" if por == TipoFechaCita.FECHA_CITA else "citaFechaCreacion"
        return [
            CitaSalutem.desde_api(c)
            for c in self.citas.values()
            if c[campo][:10] == dia.isoformat() and c["estadoCitaId"] == int(estado)
        ]

    def llamadas_a(self, metodo: str) -> list[tuple]:
        return [ll for ll in self.llamadas if ll[0] == metodo]
