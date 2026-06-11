"""Schemas Pydantic v2 para el módulo de agendamiento (EPIC-08).

GenerarPropuestaRequest calcula fecha_fin automáticamente según el tipo de propuesta,
evitando que el cliente deba calcular rangos de fechas.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agendamiento.enums import (
    DiaSemana,
    EstadoCita,
    EstadoPropuesta,
    PrioridadCita,
    TipoPropuesta,
)


# ─── Disponibilidad ────────────────────────────────────────────────────────────

class DisponibilidadProfCreate(BaseModel):
    profesional_id: int
    dia_semana: DiaSemana
    cupo_diario: int = Field(ge=1)

    @field_validator("dia_semana", mode="before")
    @classmethod
    def solo_dias_habiles(cls, v: int | DiaSemana) -> DiaSemana:
        val = int(v)
        if val not in {1, 2, 3, 4, 5}:
            raise ValueError("dia_semana debe ser 1–5 (lunes–viernes). No se permiten fines de semana.")
        return DiaSemana(val)


class DisponibilidadProfRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profesional_id: int
    dia_semana: int
    cupo_diario: int
    activo: bool
    created_at: datetime


# ─── Propuesta ─────────────────────────────────────────────────────────────────

class GenerarPropuestaRequest(BaseModel):
    """Parámetros de generación de una propuesta de agenda.

    fecha_inicio debe ser un día hábil (lun–vie).
    fecha_fin se calcula automáticamente según el tipo:
      - diaria: misma fecha que fecha_inicio
      - semanal: viernes de la semana de fecha_inicio
      - mensual: último día del mes de fecha_inicio
    """

    profesional_id: int
    tipo: TipoPropuesta
    fecha_inicio: date
    fecha_fin: date = Field(default=None)  # type: ignore[assignment]

    @field_validator("fecha_inicio")
    @classmethod
    def debe_ser_dia_habil(cls, v: date) -> date:
        if v.isoweekday() > 5:
            raise ValueError(
                f"fecha_inicio {v} es fin de semana. Solo se aceptan días hábiles (lun–vie)."
            )
        return v

    @model_validator(mode="after")
    def calcular_fecha_fin(self) -> "GenerarPropuestaRequest":
        if self.tipo == TipoPropuesta.DIARIA:
            self.fecha_fin = self.fecha_inicio
        elif self.tipo == TipoPropuesta.SEMANAL:
            # viernes de la semana (isoweekday=5)
            dias_hasta_viernes = 5 - self.fecha_inicio.isoweekday()
            self.fecha_fin = self.fecha_inicio + timedelta(days=dias_hasta_viernes)
        elif self.tipo == TipoPropuesta.MENSUAL:
            ultimo = calendar.monthrange(self.fecha_inicio.year, self.fecha_inicio.month)[1]
            self.fecha_fin = date(self.fecha_inicio.year, self.fecha_inicio.month, ultimo)
        return self


class PropuestaAgendaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profesional_id: int
    tipo: TipoPropuesta
    fecha_inicio: date
    fecha_fin: date
    estado: EstadoPropuesta
    generado_por: str
    created_at: datetime


# ─── Cita propuesta ────────────────────────────────────────────────────────────

class CitaPropuestaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    propuesta_id: int
    paciente_id: int
    fecha_candidata: date
    prioridad: PrioridadCita
    razon: str
    estado: EstadoCita
    excluida_por: str | None
    created_at: datetime


class ConfirmarCitasRequest(BaseModel):
    """IDs de CitaPropuesta a confirmar (deben pertenecer a la misma propuesta)."""
    cita_ids: list[int] = Field(min_length=1)
