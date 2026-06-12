"""Schemas del recurso Licencias para la API de integración (CEPA-121 CA-4).

Usa los nombres reales del modelo LicenciaMedica de EPIC-07:
  cantidad_dias, tipo_lm, fecha_inicio, fecha_termino, anulada.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict


class LicenciaRead(BaseModel):
    """Lectura de una licencia médica (campos reales de LicenciaMedica)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_lm: str
    cantidad_dias: int
    fecha_inicio: date
    fecha_termino: date
    diagnostico: str
    anulada: bool


class LicenciasResponse(BaseModel):
    """Respuesta del endpoint de licencias: historial + días acumulados (CA-4 RN-5)."""

    folio: str
    historial: list[LicenciaRead]
    dias_acumulados: int
