"""Listas cerradas del módulo de agendamiento (EPIC-08).

Modelos como Enums de str: validación en capa de aplicación, sin tipos enum de motor (D15).
"""

from enum import Enum


class TipoPropuesta(str, Enum):
    """Horizonte de la propuesta de agenda."""
    DIARIA = "diaria"
    SEMANAL = "semanal"
    MENSUAL = "mensual"


class EstadoPropuesta(str, Enum):
    """Estado de ciclo de vida de una propuesta."""
    BORRADOR = "borrador"
    CONFIRMADA = "confirmada"
    DESCARTADA = "descartada"


class EstadoCita(str, Enum):
    """Estado de una cita dentro de una propuesta."""
    PROPUESTA = "propuesta"
    CONFIRMADA = "confirmada"
    DESCARTADA = "descartada"


class PrioridadCita(str, Enum):
    """Prioridad de candidatura según RN-2."""
    CONTROL_VENCIDO = "control_vencido"      # (1) más alta
    CONTROL_PROXIMO = "control_proximo"       # (2)
    SEGUIMIENTO_RECETA = "seguimiento_receta" # (3)


class DiaSemana(int, Enum):
    """ISO weekday: 1=lunes … 5=viernes (no se admiten 6=sáb, 7=dom — RN-4)."""
    LUNES = 1
    MARTES = 2
    MIERCOLES = 3
    JUEVES = 4
    VIERNES = 5
