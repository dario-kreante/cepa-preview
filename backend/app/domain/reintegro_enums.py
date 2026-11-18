"""Listas cerradas del módulo de Seguimiento de Reintegro (EPIC-04).

TipoDerivacion ya existe en app.domain.enums (EPIC-01); aquí solo se definen
los enums específicos del reintegro.

TipoReca es el catálogo de calificación RECA fijado en Decisiones v5 D20. El
control médico (CEPA-062) lo usa también como `EstadoReca`.
"""

from datetime import date
from enum import Enum

from app.domain.enums import TipoAlta  # noqa: F401


class EstadoReintegro(str, Enum):
    """Estado del proceso de reintegro (CEPA-042 RN-1)."""

    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    TOTAL = "total"


class EstadoSolicitudReca(str, Enum):
    """Estado de la solicitud de RECA, derivado (QA-003, PRD v5 §7.4.2): no se guarda."""

    PENDIENTE = "pendiente"
    SOLICITADA = "solicitada"
    RECIBIDA = "recibida"


def estado_solicitud_reca(fecha_solicitud: "date | None", tiene_reca: bool) -> EstadoSolicitudReca:
    """«Recibida» si el caso tiene RECA; si no, «solicitada» con fecha de solicitud, o «pendiente»."""
    if tiene_reca:
        return EstadoSolicitudReca.RECIBIDA
    if fecha_solicitud is not None:
        return EstadoSolicitudReca.SOLICITADA
    return EstadoSolicitudReca.PENDIENTE


class TipoTrabajador(str, Enum):
    """Relación laboral del trabajador del caso de reintegro (QA-008)."""

    DEPENDIENTE = "dependiente"
    INDEPENDIENTE = "independiente"


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
