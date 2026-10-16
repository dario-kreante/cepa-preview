"""Scheduler puro (sin I/O) para EPIC-08 — Agendamiento Inteligente.

Todas las funciones son puras: reciben datos en memoria y devuelven resultados.
Sin sesiones de BD, sin side effects. Esto facilita los tests exhaustivos
y permite que la lista de pacientes por citar llame al reparto con datos ya cargados.

Reglas de negocio implementadas:
  RN-1: reposo prevalece sobre cualquier criterio de inclusión.
  RN-2: prioridad (1) control_vencido > (2) control_proximo > (3) seguimiento_receta;
         a igual prioridad, más antiguo primero (fecha_ctrl más lejana en el pasado).
  RN-3: nunca se supera el cupo del profesional para el día; el exceso queda sin cupo.
  RN-4: solo días hábiles (isoweekday 1–5) y no feriados.
  RN-5: el reposo se evalúa contra la fecha candidata, no contra la fecha de hoy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import NamedTuple

from app.agendamiento.enums import PrioridadCita

# ─── Tipos de datos para el scheduler ──────────────────────────────────────────

class ReposoPaciente(NamedTuple):
    inicio: date
    fin: date


class DisponibilidadDia(NamedTuple):
    dia_semana: int   # ISO weekday 1–5
    cupo: int


@dataclass
class Candidato:
    """Paciente candidato a ser agendado, con su contexto de prioridad."""
    paciente_id: int
    prioridad: PrioridadCita
    razon: str
    fecha_ctrl: date | None        # fecha del control (vencido o próximo); None si es receta
    reposos: list[ReposoPaciente] = field(default_factory=list)


@dataclass
class ResultadoCandidato:
    """Resultado de la evaluación de un candidato para una fecha concreta."""
    paciente_id: int
    fecha_candidata: date
    prioridad: PrioridadCita
    razon: str
    excluida_por: str | None      # None = candidato propuesto; str = motivo de exclusión


# ─── Utilidades ────────────────────────────────────────────────────────────────

_ORDEN_PRIORIDAD: dict[PrioridadCita, int] = {
    PrioridadCita.CONTROL_VENCIDO: 0,
    PrioridadCita.CONTROL_PROXIMO: 1,
    PrioridadCita.SEGUIMIENTO_RECETA: 2,
}

_FECHA_CTRL_MAX = date(9999, 12, 31)  # sentinela para candidatos sin fecha_ctrl


def tiene_reposo_vigente(reposos: list[ReposoPaciente], fecha: date) -> bool:
    """True si la fecha cae dentro de alguno de los períodos de reposo (RN-1, RN-5)."""
    return any(r.inicio <= fecha <= r.fin for r in reposos)


def _cupo_para_dia(disponibilidad: list[DisponibilidadDia], fecha: date) -> int:
    """Retorna el cupo del profesional para la fecha, o 0 si no tiene disponibilidad."""
    dow = fecha.isoweekday()
    for d in disponibilidad:
        if d.dia_semana == dow:
            return d.cupo
    return 0


def _clave_orden(c: Candidato) -> tuple[int, date]:
    """Clave de ordenamiento para RN-2: (nivel_prioridad, fecha_ctrl asc)."""
    nivel = _ORDEN_PRIORIDAD[c.prioridad]
    fecha = c.fecha_ctrl if c.fecha_ctrl is not None else _FECHA_CTRL_MAX
    return (nivel, fecha)


def _reposo_vigente_hasta(reposos: list[ReposoPaciente], fecha: date) -> date | None:
    """Retorna la fecha_fin del reposo que cubre la fecha dada, o None."""
    for r in reposos:
        if r.inicio <= fecha <= r.fin:
            return r.fin
    return None


def _dias_habiles_en_rango(inicio: date, fin: date) -> list[date]:
    """Retorna la lista de días hábiles (lun–vie) entre inicio y fin, inclusive."""
    dias: list[date] = []
    actual = inicio
    while actual <= fin:
        if actual.isoweekday() <= 5:
            dias.append(actual)
        actual += timedelta(days=1)
    return dias


# ─── Reparto de carga (feriados y sin cupo) ────────────────────────────────────

@dataclass
class CargaDia:
    """Cupo de un día hábil y cuántos pacientes se asignaron en él."""
    fecha: date
    cupo: int
    asignados: int


@dataclass
class Reparto:
    """Resultado de repartir candidatos sobre un rango de días."""
    asignados: list[ResultadoCandidato]   # excluida_por es None; fecha_candidata = día sugerido
    en_reposo: list[ResultadoCandidato]   # excluida_por = "reposo vigente hasta AAAA-MM-DD"
    sin_cupo: list[Candidato]             # no cupieron en ningún día hábil del rango
    por_dia: list[CargaDia]               # solo días hábiles no feriados con cupo > 0, en orden


def repartir_carga(
    candidatos: list[Candidato],
    desde: date,
    hasta: date,
    disponibilidad: list[DisponibilidadDia],
    festivos: frozenset[date] = frozenset(),
) -> Reparto:
    """Reparte candidatos sobre los días hábiles no feriados del rango.

    Por cada candidato (orden RN-2) se asigna el primer día con cupo restante y sin reposo
    vigente (RN-5). Si no se asignó y hubo reposo en algún día con cupo, va a en_reposo; en otro
    caso, a sin_cupo.
    Los días en festivos no tienen cupo.
    """
    dias = [d for d in _dias_habiles_en_rango(desde, hasta) if d not in festivos]

    cargas: dict[date, CargaDia] = {}
    for d in dias:
        cupo = _cupo_para_dia(disponibilidad, d)
        if cupo > 0:
            cargas[d] = CargaDia(fecha=d, cupo=cupo, asignados=0)

    asignados: list[ResultadoCandidato] = []
    en_reposo: list[ResultadoCandidato] = []
    sin_cupo: list[Candidato] = []

    primer_dia_con_cupo = next(iter(cargas), None)

    for c in sorted(candidatos, key=_clave_orden):
        asignado = False
        primer_reposo_fin: date | None = None

        for d, carga in cargas.items():
            if carga.asignados >= carga.cupo:
                continue  # cupo agotado

            fin_reposo = _reposo_vigente_hasta(c.reposos, d)
            if fin_reposo is not None:
                if primer_reposo_fin is None:
                    primer_reposo_fin = fin_reposo
                continue  # buscar otro día

            asignados.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=d,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=None,
            ))
            carga.asignados += 1
            asignado = True
            break

        if asignado:
            continue

        if primer_reposo_fin is not None and primer_dia_con_cupo is not None:
            en_reposo.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=primer_dia_con_cupo,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=f"reposo vigente hasta {primer_reposo_fin.isoformat()}",
            ))
        else:
            sin_cupo.append(c)

    return Reparto(
        asignados=asignados,
        en_reposo=en_reposo,
        sin_cupo=sin_cupo,
        por_dia=list(cargas.values()),
    )
