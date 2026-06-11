"""Listas cerradas del módulo de Seguimiento de Reintegro (EPIC-04).

TipoDerivacion ya existe en app.domain.enums (EPIC-01); aquí solo se definen
los enums específicos del reintegro.

NOTA: el catálogo definitivo de TipoReca y los riesgos calificados está
pendiente de confirmación con Coordinación (Decisiones v4, CEPA-041 nota).
Esta lista provisional (AT / EP) es suficiente para pasar tests; ampliar
cuando el equipo gestor CEPA entregue el catálogo completo.
"""

from enum import Enum

from app.domain.enums import TipoAlta  # noqa: F401


class EstadoReintegro(str, Enum):
    """Estado del proceso de reintegro (CEPA-042 RN-1)."""

    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    TOTAL = "total"


class TipoReca(str, Enum):
    """Tipo de RECA (Resolución de Calificación). Lista provisional — confirmar catálogo."""

    AT = "AT"   # Accidente del Trabajo
    EP = "EP"   # Enfermedad Profesional


# TipoAlta is re-exported from app.domain.enums to avoid duplication.
# The import at the top of this module provides the re-export.
