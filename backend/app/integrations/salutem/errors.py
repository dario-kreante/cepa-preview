"""Errores de la integración SALUTEM.

La API de SALUTEM responde SIEMPRE HTTP 200, incluso ante una api-key inválida
o un parámetro faltante: el resultado real viaja en el cuerpo, en `estado` y
`mensaje`. Un cliente que se apoye en `raise_for_status()` nunca detectaría un
fallo, así que la traducción de `mensaje` a esta jerarquía es obligatoria.

Además `estado` cambia de tipo entre respuestas: booleano ``True`` en éxito y
string ``"false"`` en error. Por eso se normaliza en vez de compararlo directo.

Verificado contra el ambiente QA (empresa 96) el 2026-09-07.
"""


class SalutemError(Exception):
    """Base de todos los fallos de la integración SALUTEM."""

    def __init__(self, mensaje: str, *, codigo: str | None = None) -> None:
        super().__init__(mensaje)
        self.codigo = codigo


class SalutemAuthError(SalutemError):
    """api-key rechazada, o empresa sin integración habilitada."""


class SalutemRequestError(SalutemError):
    """Petición no aceptada: parámetro ausente, formato o rango inválido."""


class SalutemUnavailableError(SalutemError):
    """Falla de transporte o respuesta ilegible (timeout, cuerpo no JSON)."""


# Códigos observados en QA. Los que no estén acá se tratan como SalutemError.
CODIGOS_AUTH = frozenset(
    {
        "API_KEY_NO_VALIDA",
        "SIN_INTEGRACION_CONFIGURADA",
    }
)

CODIGOS_PETICION = frozenset(
    {
        "ERROR_PETICION_NO_SOPORTADA",
        "ERROR_ESTADO_ID_NO_INGRESADO",
        "ERROR_INTERVALO_SUPERADO",
        "ERROR_FECHA_INICIO_NO_VALIDA",
        "ERROR_FECHA_TERMINO_NO_VALIDA",
        # RUT mal formado. Es distinto de ERROR_PERSONA_NO_EXISTE: acá el dato
        # que mandamos está mal, no es que la persona falte en SALUTEM.
        "ERROR_IDENTIFICACION_NO_VALIDA",
    }
)

# "No existe" no es una falla: el cliente lo traduce a None / lista vacía.
CODIGOS_NO_ENCONTRADO = frozenset(
    {
        "ERROR_PERSONA_NO_EXISTE",
        "ERROR_ATENCION_NO_EXISTE",
        "ERROR_CITA_NO_EXISTE",
    }
)


def error_desde_codigo(codigo: str) -> SalutemError:
    """Traduce un `mensaje` de SALUTEM a la excepción que le corresponde."""
    if codigo in CODIGOS_AUTH:
        return SalutemAuthError(f"SALUTEM rechazó la credencial: {codigo}", codigo=codigo)
    if codigo in CODIGOS_PETICION:
        return SalutemRequestError(f"SALUTEM rechazó la petición: {codigo}", codigo=codigo)
    return SalutemError(f"SALUTEM devolvió un error no catalogado: {codigo}", codigo=codigo)
