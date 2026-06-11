"""Enums del dominio EPT (EPIC-03).

Listas cerradas validadas en la capa de aplicación (Pydantic).
Columnas correspondientes usan String(40) para portabilidad (D15).
"""

from enum import Enum


class FactorRiesgo(str, Enum):
    """Factor de riesgo del puesto laboral (CEPA-030 RN-1).

    Nota: confirmación pendiente de si es lista cerrada definitiva o parametrizable
    (pregunta abierta del spec). Esta lista cubre los valores del Excel de origen.
    Se trata como lista cerrada P0; se puede ampliar como migración de datos.
    """

    CARGA = "carga"
    ORGANIZACION_TRABAJO = "organizacion_trabajo"
    FACTORES_PSICOSOCIALES = "factores_psicosociales"
    VIOLENCIA_LABORAL = "violencia_laboral"
    CONDICIONES_ERGONOMICAS = "condiciones_ergonomicas"
    OTRO = "otro"


class EstadoEpt(str, Enum):
    """Estado del caso EPT."""

    ABIERTO = "abierto"
    NO_CORRESPONDE = "no_corresponde"
    CERRADO = "cerrado"


class EstadoCumplimiento(str, Enum):
    """Estado de cumplimiento de un plazo regulatorio EPT (CEPA-032 RN-1)."""

    EN_PLAZO = "en_plazo"
    POR_VENCER = "por_vencer"
    VENCIDO = "vencido"
    CUMPLIDO = "cumplido"
