"""Listas cerradas del módulo de Controles Médicos (EPIC-06).

Se modelan como Enums de str para validación en capa de aplicación (Pydantic).
No se usan tipos enum nativos del motor (portabilidad D15).
"""

from enum import Enum

from app.domain.reintegro_enums import TipoReca


class TipoReposo(str, Enum):
    """Tipo de reposo de la licencia médica (CEPA-062 RN-2)."""

    TOTAL = "total"
    PARCIAL = "parcial"


class TipoLicencia(str, Enum):
    """Tipos de licencia médica válidos (§7.7.1 / CEPA-062 RN-4).

    Incluye licencias extra-sistema (Decisiones v4 D7).
    """

    TIPO_1 = "1"
    TIPO_5 = "5"
    TIPO_6 = "6"
    TIPO_3 = "3"
    TIPO_4 = "4"
    EXTRA_SISTEMA = "extra_sistema"


# Calificación RECA asociada al control (CEPA-062 RN-5). Es el mismo catálogo que
# la RECA del reintegro (Decisiones v5 D20); antes era un estado de flujo.
EstadoReca = TipoReca
