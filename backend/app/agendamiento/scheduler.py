"""Scheduler puro (sin I/O) para EPIC-08 — Agendamiento Inteligente.

Todas las funciones son puras: reciben datos en memoria y devuelven resultados.
Sin sesiones de BD, sin side effects. Esto facilita los tests exhaustivos
y permite que el service llame al scheduler con datos ya cargados.

Reglas de negocio implementadas:
  RN-1: reposo prevalece sobre cualquier criterio de inclusión.
  RN-2: prioridad (1) control_vencido > (2) control_proximo > (3) seguimiento_receta;
         a igual prioridad, más antiguo primero (fecha_ctrl más lejana en el pasado).
  RN-3: nunca se supera el cupo del profesional para el día; el exceso se difiere.
  RN-4: solo días hábiles (isoweekday 1–5); fines de semana retornan lista vacía.
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


# ─── Propuesta diaria ──────────────────────────────────────────────────────────

def proponer_agenda(
    candidatos: list[Candidato],
    fecha: date,
    disponibilidad: list[DisponibilidadDia],
) -> list[ResultadoCandidato]:
    """Genera propuesta para un día concreto.

    Retorna lista de ResultadoCandidato. Los candidatos excluidos aparecen en la lista
    con excluida_por != None (para que el llamador pueda reportar el motivo — CA-4).
    Los candidatos propuestos tienen excluida_por == None.

    Si la fecha es fin de semana o el profesional no tiene disponibilidad, devuelve [].
    """
    if fecha.isoweekday() > 5:
        return []

    cupo = _cupo_para_dia(disponibilidad, fecha)
    if cupo == 0:
        return []

    candidatos_ordenados = sorted(candidatos, key=_clave_orden)
    resultado: list[ResultadoCandidato] = []
    propuestos = 0

    for c in candidatos_ordenados:
        fin_reposo = _reposo_vigente_hasta(c.reposos, fecha)
        if fin_reposo is not None:
            resultado.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=fecha,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=f"reposo vigente hasta {fin_reposo.isoformat()}",
            ))
            continue

        if propuestos >= cupo:
            # Cupo agotado: el candidato se omite de este día
            # (será recogido por proponer_agenda_semana para el día siguiente)
            continue

        resultado.append(ResultadoCandidato(
            paciente_id=c.paciente_id,
            fecha_candidata=fecha,
            prioridad=c.prioridad,
            razon=c.razon,
            excluida_por=None,
        ))
        propuestos += 1

    return resultado


# ─── Propuesta semanal/mensual ─────────────────────────────────────────────────

def _dias_habiles_en_rango(inicio: date, fin: date) -> list[date]:
    """Retorna la lista de días hábiles (lun–vie) entre inicio y fin, inclusive."""
    dias: list[date] = []
    actual = inicio
    while actual <= fin:
        if actual.isoweekday() <= 5:
            dias.append(actual)
        actual += timedelta(days=1)
    return dias


def proponer_agenda_semana(
    candidatos: list[Candidato],
    semana_inicio: date,
    semana_fin: date,
    disponibilidad: list[DisponibilidadDia],
) -> list[ResultadoCandidato]:
    """Distribuye candidatos a lo largo de los días hábiles del rango (semanal o mensual).

    Algoritmo:
    1. Ordenar candidatos por RN-2 (prioridad + antigüedad).
    2. Para cada candidato, asignar el primer día hábil donde:
       a. El profesional tiene disponibilidad.
       b. El paciente no tiene reposo vigente ese día (RN-5).
       c. El cupo de ese día no está agotado (RN-3).
    3. Si el candidato tiene reposo en todos los días del rango, queda excluido
       con el motivo del primer reposo encontrado.
    4. El exceso de candidatos que no caben en ningún día del rango queda sin proponer
       (no se incluyen en el resultado — se diferirán a la siguiente semana/mes si el
       caller llama de nuevo con el rango extendido).

    Retorna la lista plana de ResultadoCandidato de todos los días del rango,
    incluyendo los excluidos por reposo.
    """
    dias = _dias_habiles_en_rango(semana_inicio, semana_fin)
    if not dias:
        return []

    # Cupo disponible por día
    cupo_restante: dict[date, int] = {}
    for d in dias:
        c = _cupo_para_dia(disponibilidad, d)
        if c > 0:
            cupo_restante[d] = c

    candidatos_ordenados = sorted(candidatos, key=_clave_orden)
    resultado: list[ResultadoCandidato] = []

    for c in candidatos_ordenados:
        asignado = False
        primer_reposo_fin: date | None = None

        for d in dias:
            if d not in cupo_restante:
                continue  # sin disponibilidad ese día o cupo agotado

            fin_reposo = _reposo_vigente_hasta(c.reposos, d)
            if fin_reposo is not None:
                if primer_reposo_fin is None:
                    primer_reposo_fin = fin_reposo
                continue  # buscar otro día

            # Disponibilidad + sin reposo + cupo
            resultado.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=d,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=None,
            ))
            cupo_restante[d] -= 1
            if cupo_restante[d] == 0:
                del cupo_restante[d]
            asignado = True
            break

        if not asignado and primer_reposo_fin is not None:
            # Excluido por reposo en todos los días del rango donde había disponibilidad
            primer_dia_con_disp = next(
                (d for d in dias if _cupo_para_dia(disponibilidad, d) > 0), dias[0]
            )
            resultado.append(ResultadoCandidato(
                paciente_id=c.paciente_id,
                fecha_candidata=primer_dia_con_disp,
                prioridad=c.prioridad,
                razon=c.razon,
                excluida_por=f"reposo vigente hasta {primer_reposo_fin.isoformat()}",
            ))

    return resultado
