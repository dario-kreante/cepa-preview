"""Listas cerradas del módulo de alertas y notificaciones (EPIC-10).

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo portabilidad de BD (no se usan tipos enum nativos del motor).
"""

from enum import Enum


class TipoAlerta(str, Enum):
    """Los 7 tipos de alerta soportados (RN-1 de CEPA-100)."""

    CONTROL_MEDICO = "control_medico"
    VENCIMIENTO_LICENCIA = "vencimiento_licencia"
    PLAZO_EPT = "plazo_ept"
    PLAZO_ISL = "plazo_isl"
    CONSENTIMIENTO_PENDIENTE = "consentimiento_pendiente"
    RECETA_POR_RENOVAR = "receta_por_renovar"
    ODA_POR_VENCER = "oda_por_vencer"


class EstadoAlerta(str, Enum):
    """Estados del ciclo de vida de una alerta (RN-5 de CEPA-101)."""

    PENDIENTE = "pendiente"
    LEIDA = "leida"
    RESUELTA = "resuelta"


class EstadoTarea(str, Enum):
    """Estados de una tarea operativa (RN-3 de CEPA-103)."""

    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
