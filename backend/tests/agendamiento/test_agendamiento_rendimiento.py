"""TC-080-10: Propuesta mensual con volumen objetivo (< 2 s, PRD §9).

Requiere dataset poblado. Correr con:
    uv run pytest tests/agendamiento/test_agendamiento_rendimiento.py -m rendimiento -v
"""

import time
from datetime import date, timedelta

import pytest

from app.agendamiento.enums import PrioridadCita
from app.agendamiento.scheduler import (
    Candidato,
    DisponibilidadDia,
    ReposoPaciente,
    proponer_agenda_semana,
)


pytestmark = pytest.mark.rendimiento

LIMITE_SEGUNDOS = 2.0


def _generar_candidatos_volumen(n: int) -> list[Candidato]:
    """Genera n candidatos con reposos distribuidos aleatoriamente."""
    import random
    random.seed(42)
    hoy = date(2026, 7, 1)
    candidatos = []
    prioridades = list(PrioridadCita)
    for i in range(1, n + 1):
        prioridad = prioridades[i % len(prioridades)]
        reposos = []
        if random.random() < 0.15:  # ~15% tienen reposo
            ini = hoy + timedelta(days=random.randint(0, 15))
            fin = ini + timedelta(days=random.randint(3, 14))
            reposos = [ReposoPaciente(inicio=ini, fin=fin)]
        candidatos.append(Candidato(
            paciente_id=i,
            prioridad=prioridad,
            razon=f"razon_{i}",
            fecha_ctrl=hoy - timedelta(days=i % 30),
            reposos=reposos,
        ))
    return candidatos


def test_tc_080_10_propuesta_mensual_menos_de_2s():
    """TC-080-10: 800 candidatos (volumen objetivo), mes completo, 25 prof → < 2 s."""
    candidatos = _generar_candidatos_volumen(800)
    disponibilidad = [DisponibilidadDia(dia_semana=d, cupo=8) for d in range(1, 6)]
    mes_inicio = date(2026, 7, 1)
    mes_fin = date(2026, 7, 31)

    inicio = time.perf_counter()
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=mes_inicio,
        semana_fin=mes_fin,
        disponibilidad=disponibilidad,
    )
    elapsed = time.perf_counter() - inicio

    assert elapsed < LIMITE_SEGUNDOS, (
        f"La propuesta mensual tardó {elapsed:.3f} s (límite {LIMITE_SEGUNDOS} s). "
        "Revisar complejidad del scheduler."
    )
    assert len(resultado) > 0


def test_tc_080_10_reposo_evaluado_dia_a_dia_en_volumen():
    """RN-5 con volumen: la exclusión por reposo funciona correctamente a escala."""
    # Todos los candidatos tienen reposo en la primera semana del mes
    reposo_semana1 = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 5))]
    candidatos = [
        Candidato(
            paciente_id=i,
            prioridad=PrioridadCita.CONTROL_PROXIMO,
            razon=f"ctrl {i}",
            fecha_ctrl=date(2026, 7, 10),
            reposos=reposo_semana1,
        )
        for i in range(1, 101)
    ]
    disponibilidad = [DisponibilidadDia(dia_semana=d, cupo=8) for d in range(1, 6)]
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=date(2026, 7, 1),
        semana_fin=date(2026, 7, 31),
        disponibilidad=disponibilidad,
    )
    # Ningún propuesto debe tener fecha_candidata en la semana 1 (01–05 julio)
    for r in resultado:
        if r.excluida_por is None:
            assert r.fecha_candidata >= date(2026, 7, 6), (
                f"Cita propuesta en día con reposo: {r.fecha_candidata}"
            )
