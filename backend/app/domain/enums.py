"""Listas cerradas del dominio CEPA (Decisiones v4 D4, D6).

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo la portabilidad de BD (no se usan tipos enum nativos del motor).
"""

from enum import Enum


class TipoDerivacion(str, Enum):
    """Tipos de derivación permitidos (v4 D4). 'SOCORRO' ya no es válido."""

    DIEP = "DIEP"
    DIAT = "DIAT"
    PAPT_FLUJO_AT = "PAPT a flujo AT"
    REINGRESO_FUMP = "Reingreso FUMP"
    REINGRESO_SUSESO = "Reingreso SUSESO"
    CONVENIO_U_CLINICA = "Convenio U.Clinica"
    PROYECTO = "Proyecto"
    PARTICULAR = "Particular"
    PAPT = "PAPT"


class TipoIngreso(str, Enum):
    """Tipo de ingreso (v4 D6 / dashboard D5)."""

    CONSULTA_ESPONTANEA = "consulta_espontanea"
    CONVENIO = "convenio"
    PROYECTO = "proyecto"
    PARTICULAR = "particular"


class Sexo(str, Enum):
    F = "F"
    M = "M"
    OTRO = "otro"


class EstadoCaso(str, Enum):
    """Estados de caso válidos (§7.1.3)."""

    ACTIVO = "activo"
    CERRADO = "cerrado"
    DERIVADO = "derivado"


class TipoAlta(str, Enum):
    """Tipos de alta válidos (§7.1.3, v4 D6)."""

    TERAPEUTICA = "terapeutica"
    MEDICA = "medica"
    PSICOLOGICA = "psicologica"
    ABANDONO = "abandono"
    DERIVACION = "derivacion"


class EstadoEvaluacion(str, Enum):
    """Estados de evaluación médica/psicológica (§7.1.2 RN-2)."""

    REALIZADA = "realizada"
    PENDIENTE = "pendiente"
    NO_APLICA = "no_aplica"


class EstadoConsentimiento(str, Enum):
    """Estado del consentimiento informado (CEPA-016 RN-2)."""

    FIRMADO = "firmado"
    PENDIENTE = "pendiente"
