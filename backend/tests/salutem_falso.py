"""SALUTEM en memoria para probar el sync sin red.

Implementa `SalutemClientProtocol` con los mismos formatos crudos que la API
real (claves camelCase, fechas como string) y registra cada llamada.
"""

from datetime import date

from app.integrations.salutem.errors import (
    SalutemAuthError,
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


class SalutemFalso:
    def __init__(self) -> None:
        self.personas: dict[int, dict] = {}
        self.citas: dict[int, dict] = {}
        self.atenciones: dict[int, dict] = {}
        self.llamadas: list[tuple] = []
        # (dia, estado) que SALUTEM rechaza con SalutemRequestError.
        self.dias_con_error: set[tuple[date, int]] = set()
        # Cuántas de las próximas llamadas fallan con SalutemUnavailableError.
        self.caidas_pendientes = 0
        self.credencial_rechazada = False

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
        for p in self.personas.values():
            if p["identificacion"] == rut:
                return PersonaSalutem.desde_api(p)
        return None

    def obtener_persona(self, salutem_id: int) -> PersonaSalutem | None:
        self._registrar("obtener_persona", salutem_id)
        p = self.personas.get(salutem_id)
        return PersonaSalutem.desde_api(p) if p else None

    def listar_atenciones(self, salutem_id: int) -> list[CitaSalutem]:
        self._registrar("listar_atenciones", salutem_id)
        return [
            CitaSalutem.desde_api(self.citas[cita_id])
            for cita_id in self.atenciones
            if self.citas[cita_id]["personaId"] == salutem_id
        ]

    def obtener_atencion(self, salutem_id: int, cita_id: int) -> AtencionSalutem | None:
        self._registrar("obtener_atencion", salutem_id, cita_id)
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
        if (dia, int(estado)) in self.dias_con_error:
            raise SalutemRequestError("rechazada", codigo="ERROR_INTERVALO_SUPERADO")
        campo = "citaFecha" if por == TipoFechaCita.FECHA_CITA else "citaFechaCreacion"
        return [
            CitaSalutem.desde_api(c)
            for c in self.citas.values()
            if c[campo][:10] == dia.isoformat() and c["estadoCitaId"] == int(estado)
        ]

    def llamadas_a(self, metodo: str) -> list[tuple]:
        return [ll for ll in self.llamadas if ll[0] == metodo]
