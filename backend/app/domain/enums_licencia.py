"""Listas cerradas del dominio de Licencias Médicas — EPIC-07.

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo la portabilidad de BD (no se usan tipos enum nativos del motor — D15).
"""

from enum import Enum


class TipoLicencia(str, Enum):
    """Tipos de licencia médica relevantes para CEPA (RN-3 CEPA-070).

    1 = enfermedad común
    5 = enfermedad/accidente del trabajo curativa
    6 = patología del embarazo / prórroga
    """

    UNO = "1"
    CINCO = "5"
    SEIS = "6"


class TipoReposo(str, Enum):
    """Tipo de reposo prescrito en la LM (RN-3 CEPA-070, v4 D8)."""

    TOTAL = "total"
    PARCIAL = "parcial"


class EstadoEnvioISL(str, Enum):
    """Estado de envío de la LM al Instituto de Seguridad Laboral (RN-2 CEPA-073)."""

    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    RECHAZADO = "rechazado"


class OrigenLicencia(str, Enum):
    """Origen de la licencia: gestionada en CEPA o registrada como extra-sistema (v4 D7)."""

    SISTEMA = "sistema"
    EXTRA_SISTEMA = "extra_sistema"
