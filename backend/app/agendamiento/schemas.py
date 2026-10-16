"""Schemas Pydantic v2 para el módulo de agendamiento (EPIC-08).

Las propuestas ya no se generan desde el SIGE (las horas se agendan en SALUTEM); quedan los
schemas de lectura del historial.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agendamiento.enums import (
    DiaSemana,
    EstadoCita,
    EstadoPropuesta,
    PrioridadCita,
    ResultadoGestion,
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


# ─── Gestión de contacto ───────────────────────────────────────────────────────

class GestionCreate(BaseModel):
    profesional_id: int
    resultado: ResultadoGestion
    nota: str | None = Field(default=None, max_length=300)

    @field_validator("nota")
    @classmethod
    def _normalizar_nota(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return " ".join(v.split()) or None


class GestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    profesional_id: int
    resultado: ResultadoGestion
    nota: str | None
    usuario: str
    created_at: datetime


# ─── Lista de pacientes por citar ──────────────────────────────────────────────

class CargaDiaRead(BaseModel):
    fecha: date
    cupo: int
    asignados: int


class UltimaGestionRead(BaseModel):
    fecha: datetime
    resultado: ResultadoGestion
    usuario: str
    nota: str | None


class PacientePorCitarRead(BaseModel):
    paciente_id: int
    nombre: str
    folio: str | None
    prioridad: PrioridadCita
    razon: str
    fecha_objetivo: date | None
    dia_sugerido: date | None
    seccion: Literal["por_citar", "sin_cupo", "en_reposo"]
    reposo_hasta: date | None
    sin_vinculo_salutem: bool
    dijo_agendada_sin_hora: bool
    ultima_gestion: UltimaGestionRead | None


class PacientesPorCitarRead(BaseModel):
    profesional_id: int
    desde: date
    hasta: date
    por_dia: list[CargaDiaRead]
    pacientes: list[PacientePorCitarRead]
