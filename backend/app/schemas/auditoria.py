"""Schemas Pydantic v2 para el módulo de Auditoría (EPIC-05).

DTOs de solo lectura — no modifican datos clínicos.
"""
from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class SeccionDatosCasoRead(BaseModel):
    """§7.5.1 Datos del caso consolidado."""

    model_config = ConfigDict(from_attributes=True)

    folio: str
    numero_siniestro: str | None
    fecha_denuncia: datetime.date | None
    tipo_denuncia: str | None
    fecha_derivacion: datetime.date | None
    nombre_completo: str
    rut: str
    region: str | None


class SeccionEvaluacionesRead(BaseModel):
    """§7.5.2 Seguimiento de evaluaciones.

    Diagnóstico inicial y post-RECA se muestran por separado (CA-3, RN-4).
    """

    model_config = ConfigDict(from_attributes=True)

    fecha_eval_medica: datetime.date | None
    fecha_eval_psicologica: datetime.date | None
    fecha_calificacion_reca: datetime.date | None
    diagnostico_inicial: str | None
    diagnostico_post_reca: str | None
    numero_sesiones_evaluacion: int | None = None  # S2: dato no existe en el modelo real


class SeccionControlesRead(BaseModel):
    """§7.5.3 Controles y tratamiento."""

    model_config = ConfigDict(from_attributes=True)

    fecha_primera_consulta_medica: datetime.date | None
    fecha_primera_consulta_psicologica: datetime.date | None
    n_sesiones_medicas: int | None = None      # S2: dato no existe en el modelo real
    n_sesiones_psicologicas: int | None = None  # S2: dato no existe en el modelo real
    n_sesiones_ampliacion: int | None = None    # S2: dato no existe en el modelo real
    reintegro_parcial: bool
    fecha_reintegro_parcial: datetime.date | None
    reintegro_total: bool
    fecha_reintegro_total: datetime.date | None


class SeccionCierreRead(BaseModel):
    """§7.5.4 Cierre del caso.

    Cuando no hay altas registradas, todos los flags son False y las fechas None
    (caso en tratamiento — CA-5, TC-050-04). No se bloquea la visualización.
    """

    model_config = ConfigDict(from_attributes=True)

    alta_medica: bool
    fecha_alta_medica: datetime.date | None
    alta_psicologica: bool
    fecha_alta_psicologica: datetime.date | None
    alta_terapeutica: bool
    fecha_alta_terapeutica: datetime.date | None
    estado_general: str | None
    observaciones: str | None


class CasoConsolidadoRead(BaseModel):
    """Vista consolidada del caso — todas las secciones §7.5.1..§7.5.4.

    Corresponde a la respuesta del endpoint GET /api/v1/auditoria/casos/{ingreso_id}.
    """

    model_config = ConfigDict(from_attributes=True)

    ingreso_id: int
    datos_caso: SeccionDatosCasoRead
    evaluaciones: SeccionEvaluacionesRead
    controles: SeccionControlesRead
    cierre: SeccionCierreRead


class FiltrosReporte(BaseModel):
    """Filtros aplicables al generador de reportes de auditoría (CEPA-051).

    RN-2: el período (fecha_desde + fecha_hasta) es obligatorio.
    Todos los demás filtros son opcionales y combinables (AND).
    """

    fecha_desde: datetime.date
    fecha_hasta: datetime.date
    diagnostico: str | None = None
    profesional: str | None = None
    estado_caso: str | None = None
    programa: str | None = None
    tipo_alta: str | None = None
    region: str | None = None
    tipo_ingreso: str | None = None
    tipo_denuncia: str | None = None  # filtra por tipo_derivacion del Ingreso

    @field_validator("fecha_desde", "fecha_hasta", mode="before")
    @classmethod
    def _periodo_obligatorio(cls, v: object) -> object:
        if v is None:
            raise ValueError("El período (fecha_desde y fecha_hasta) es obligatorio.")
        return v


class FilaReporteRead(BaseModel):
    """Una fila del reporte de auditoría.

    Cada fila es trazable a su folio + número de siniestro (CA-3, RN-3, TC-051-03).
    """

    model_config = ConfigDict(from_attributes=True)

    ingreso_id: int
    folio: str
    numero_siniestro: str | None
    rut: str
    nombre_completo: str
    region: str | None
    fecha_denuncia: datetime.date | None
    tipo_denuncia: str | None
    estado_caso: str | None
    diagnostico_inicial: str | None
    diagnostico_post_reca: str | None
    profesional: str | None
    fecha_calificacion_reca: datetime.date | None
    reintegro_parcial: bool
    reintegro_total: bool
    alta_medica: bool
    alta_psicologica: bool
    alta_terapeutica: bool


class ReporteAuditoriaRead(BaseModel):
    """Respuesta del endpoint de generación de reportes.

    Incluye los filtros aplicados como metadatos del reporte (CA-2, RN-3).
    Un reporte vacío (total=0, filas=[]) es un resultado válido (CA-4, TC-051-04).
    """

    model_config = ConfigDict(from_attributes=True)

    filtros_aplicados: FiltrosReporte
    total: int
    filas: list[FilaReporteRead]
