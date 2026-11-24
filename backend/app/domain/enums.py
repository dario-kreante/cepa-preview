"""Listas cerradas del dominio CEPA (Decisiones v4 D4, D6).

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo la portabilidad de BD (no se usan tipos enum nativos del motor).
"""

from enum import Enum


class TipoDerivacion(str, Enum):
    """Tipos de derivación permitidos (v4 D4). 'SOCORRO' ya no es válido."""

    DIEP = "DIEP"
    DIEP_SIN_EPT = "DIEP sin EPT"  # QA 23-11-2026 (Angela): DIEP que no requiere EPT
    DIAT = "DIAT"
    PAPT_FLUJO_AT = "PAPT a flujo AT"
    REINGRESO_FUMP = "Reingreso FUMP"
    REINGRESO_SUSESO = "Reingreso SUSESO"
    REINGRESO_ISL = "Reingreso ISL"
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


class EstadoRegistroPaciente(str, Enum):
    """Estado del registro del paciente: los borradores de SALUTEM esperan su folio."""

    COMPLETO = "completo"
    PENDIENTE_FOLIO = "pendiente_folio"
    DESCARTADO = "descartado"


class OrigenPaciente(str, Enum):
    SIGE = "SIGE"
    SALUTEM = "SALUTEM"


class EstadoCaso(str, Enum):
    """Estados de caso válidos (§7.1.3)."""

    ACTIVO = "activo"
    CERRADO = "cerrado"
    DERIVADO = "derivado"
    # Reunión 29-10 (D5): el paciente dejó de asistir y deja de recibir atenciones hasta
    # firmar el encuadre. Lo cambia a mano el CEPA al revisar la alerta de posible encuadre.
    ENCUADRE = "encuadre"


class MotivoCierre(str, Enum):
    """Motivo con que se cierra un caso (QA-011). Lista propia, separada de ``TipoAlta``."""

    RECA_EC = "reca_ec"
    ALTA_MEDICA = "alta_medica"
    ALTA_ADMINISTRATIVA = "alta_administrativa"
    ABANDONO = "abandono"
    DESISTE_PROCESO = "desiste_proceso"
    CAMBIO_PRESTADOR = "cambio_prestador"


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


class EstadoFarmacologico(str, Enum):
    """Estado del caso farmacológico del paciente (CEPA-020 RN-3).

    Pendiente confirmar catálogo final con Coordinación (ver Notas de cierre).
    """

    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    COMPLETADO = "completado"
    PENDIENTE = "pendiente"


class FrecuenciaFarmaco(str, Enum):
    """Frecuencias de administración habituales para el esquema farmacológico (CEPA-021 RN-1).

    'otro' contempla frecuencias no listadas (se registra junto al campo texto).
    """

    C24H = "c/24h"
    C12H = "c/12h"
    C8H = "c/8h"
    C6H = "c/6h"
    SEMANAL = "semanal"
    BISEMANAL = "bisemanal"
    MENSUAL = "mensual"
    OTRO = "otro"
