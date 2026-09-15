"""Listas cerradas del módulo de Seguimiento de Reintegro (EPIC-04).

TipoDerivacion ya existe en app.domain.enums (EPIC-01); aquí solo se definen
los enums específicos del reintegro.

TipoReca es el catálogo de calificación RECA fijado en Decisiones v5 D20. El
control médico (CEPA-062) lo usa también como `EstadoReca`.
"""

from enum import Enum

from app.domain.enums import TipoAlta  # noqa: F401


class EstadoReintegro(str, Enum):
    """Estado del proceso de reintegro (CEPA-042 RN-1)."""

    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    TOTAL = "total"


class TipoReca(str, Enum):
    """Calificación de la RECA (Resolución de Calificación) — Decisiones v5 D20.

    El desarrollo de la sigla NPE está pendiente de confirmar con el CEPA.
    """

    EP = "EP"   # Enfermedad profesional
    EC = "EC"   # Enfermedad común
    AT = "AT"   # Accidente del trabajo
    AC = "AC"   # Accidente común
    NPE = "NPE"
    NO_APLICA = "no_aplica"


# TipoAlta is re-exported from app.domain.enums to avoid duplication.
# The import at the top of this module provides the re-export.
