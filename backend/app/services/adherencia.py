"""Cálculos de adherencia y avance de tratamiento (D5, CEPA-095).

Estas funciones puras son testeables en aislamiento (QA de métricas — D5).
"""

from __future__ import annotations


def calcular_pct_adherencia(realizadas: int, agendadas: int) -> float | None:
    """% adherencia = citas realizadas / citas agendadas * 100 (D5).

    Retorna None si agendadas == 0 (sin división por cero — TC-095-03).
    """
    if agendadas <= 0:
        return None
    return round((realizadas / agendadas) * 100, 2)


def calcular_pct_avance(
    sesiones_realizadas: int,
    sesiones_plan: int | None,
    aumentos_isl: int = 0,
) -> float | None:
    """% avance = sesiones_realizadas / (sesiones_plan + aumentos_isl) * 100 (D5).

    Retorna None si el plan es cero, None o no definido.
    Los aumentos de ISL amplían el denominador (TC-095-02).
    """
    if sesiones_plan is None or sesiones_plan <= 0:
        return None
    total_plan = sesiones_plan + aumentos_isl
    if total_plan <= 0:
        return None
    return round((sesiones_realizadas / total_plan) * 100, 2)
