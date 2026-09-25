"""Schemas del recurso Licencias para la API de integración (CEPA-121 CA-4).

Usa los nombres reales del modelo LicenciaMedica de EPIC-07:
  cantidad_dias, tipo_lm, fecha_inicio, fecha_termino, anulada.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.domain.enums_licencia import EstadoEnvioISL, TipoReposo


class LicenciaRead(BaseModel):
    """Lectura de una licencia médica (campos reales de LicenciaMedica).

    Trae todas las columnas que muestra el listado de Licencias, para que la
    pantalla no pida el detalle fila por fila (COMP-2609-04).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    folio_lm: str | None
    tipo_lm: str
    tipo_reposo: TipoReposo
    cantidad_dias: int
    fecha_inicio: date
    fecha_termino: date
    diagnostico: str
    eeag_gaf: int | None
    eeag_gaf_tramo: str | None = None
    envio_isl: EstadoEnvioISL
    anulada: bool


class LicenciasResponse(BaseModel):
    """Respuesta del endpoint de licencias: historial + días acumulados (CA-4 RN-5)."""

    folio: str
    ingreso_id: int
    historial: list[LicenciaRead]
    dias_acumulados: int
