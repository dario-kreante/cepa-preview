"""Tests exhaustivos del scheduler puro (sin BD).

Cubre todos los TC-080-XX, CA y RN del spec CEPA-080.
"""

from datetime import date, timedelta


from app.agendamiento.enums import PrioridadCita
from app.agendamiento.scheduler import (
    CargaDia,
    Candidato,
    DisponibilidadDia,
    ReposoPaciente,
    repartir_carga,
    tiene_reposo_vigente,
)


# ─── Fixtures de datos ──────────────────────────────────────────────────────────

HOY = date(2026, 7, 7)  # martes (isoweekday=2)

DISPONIBILIDAD_COMPLETA = [
    DisponibilidadDia(dia_semana=1, cupo=8),
    DisponibilidadDia(dia_semana=2, cupo=8),
    DisponibilidadDia(dia_semana=3, cupo=8),
    DisponibilidadDia(dia_semana=4, cupo=8),
    DisponibilidadDia(dia_semana=5, cupo=8),
]


def candidato_control_vencido(paciente_id: int, fecha_ctrl: date) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=PrioridadCita.CONTROL_VENCIDO,
        razon=f"control vencido desde {fecha_ctrl}",
        fecha_ctrl=fecha_ctrl,
        reposos=[],
    )


def candidato_control_proximo(paciente_id: int, fecha_ctrl: date) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=PrioridadCita.CONTROL_PROXIMO,
        razon=f"control próximo el {fecha_ctrl}",
        fecha_ctrl=fecha_ctrl,
        reposos=[],
    )


def candidato_receta(paciente_id: int) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=PrioridadCita.SEGUIMIENTO_RECETA,
        razon="seguimiento de receta",
        fecha_ctrl=None,
        reposos=[],
    )


def candidato_con_reposo(
    paciente_id: int, inicio: date, fin: date, prioridad: PrioridadCita
) -> Candidato:
    return Candidato(
        paciente_id=paciente_id,
        prioridad=prioridad,
        razon="control próximo",
        fecha_ctrl=HOY,
        reposos=[ReposoPaciente(inicio=inicio, fin=fin)],
    )


# ─── tiene_reposo_vigente ────────────────────────────────────────────────────────

def test_tiene_reposo_vigente_dentro_del_rango():
    """RN-1, RN-5: la evaluación es contra la fecha candidata, no contra hoy."""
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 5)) is True


def test_tiene_reposo_vigente_en_borde_inicio():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 1)) is True


def test_tiene_reposo_vigente_en_borde_fin():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 10)) is True


def test_no_tiene_reposo_vigente_antes():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 6, 30)) is False


def test_no_tiene_reposo_vigente_despues():
    reposos = [ReposoPaciente(inicio=date(2026, 7, 1), fin=date(2026, 7, 10))]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 11)) is False


def test_reposos_multiples_alguno_activo():
    reposos = [
        ReposoPaciente(inicio=date(2026, 6, 1), fin=date(2026, 6, 10)),
        ReposoPaciente(inicio=date(2026, 7, 5), fin=date(2026, 7, 15)),
    ]
    assert tiene_reposo_vigente(reposos, date(2026, 7, 8)) is True


def test_sin_reposos_nunca_vigente():
    assert tiene_reposo_vigente([], date(2026, 7, 7)) is False


# ─── repartir_carga: reparto de carga con feriados y sin cupo ──────────────────

def test_repartir_carga_salta_feriados():
    """Un feriado no tiene cupo: el reparto solo usa los días hábiles no feriados."""
    lunes = date(2026, 7, 6)
    martes = date(2026, 7, 7)
    candidatos = [candidato_control_vencido(i, HOY) for i in range(1, 4)]
    resultado = repartir_carga(
        candidatos=candidatos,
        desde=lunes,
        hasta=martes,
        disponibilidad=[DisponibilidadDia(dia_semana=1, cupo=2), DisponibilidadDia(dia_semana=2, cupo=2)],
        festivos=frozenset({lunes}),
    )
    assert resultado.por_dia == [CargaDia(fecha=martes, cupo=2, asignados=2)]
    assert len(resultado.asignados) == 2
    assert all(r.fecha_candidata == martes for r in resultado.asignados)
    assert len(resultado.sin_cupo) == 1
    assert resultado.en_reposo == []


def test_repartir_carga_rango_solo_fin_de_semana():
    """Un rango sábado–domingo no tiene días hábiles: todos quedan sin cupo."""
    sabado = date(2026, 7, 11)
    domingo = date(2026, 7, 12)
    candidatos = [candidato_control_vencido(1, HOY), candidato_receta(2)]
    resultado = repartir_carga(
        candidatos=candidatos,
        desde=sabado,
        hasta=domingo,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert resultado.por_dia == []
    assert resultado.asignados == []
    assert resultado.en_reposo == []
    assert len(resultado.sin_cupo) == 2


def test_repartir_carga_reposo_en_todo_el_rango_va_a_en_reposo():
    """Un paciente con reposo en todos los días del rango va a en_reposo, no a sin_cupo."""
    lunes = date(2026, 7, 6)
    viernes = date(2026, 7, 10)
    candidato = Candidato(
        paciente_id=1,
        prioridad=PrioridadCita.CONTROL_VENCIDO,
        razon="control vencido",
        fecha_ctrl=HOY,
        reposos=[ReposoPaciente(inicio=lunes, fin=viernes)],
    )
    resultado = repartir_carga(
        candidatos=[candidato],
        desde=lunes,
        hasta=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert resultado.asignados == []
    assert resultado.sin_cupo == []
    assert len(resultado.en_reposo) == 1
    assert resultado.en_reposo[0].excluida_por == f"reposo vigente hasta {viernes.isoformat()}"


def test_repartir_carga_respeta_prioridad():
    """Con cupo 1, el paciente de mayor prioridad (P1) se asigna y el P3 queda sin cupo."""
    lunes = date(2026, 7, 6)
    p3 = candidato_receta(1)
    p1 = candidato_control_vencido(2, HOY)
    resultado = repartir_carga(
        candidatos=[p3, p1],
        desde=lunes,
        hasta=lunes,
        disponibilidad=[DisponibilidadDia(dia_semana=1, cupo=1)],
    )
    assert [r.paciente_id for r in resultado.asignados] == [2]
    assert [c.paciente_id for c in resultado.sin_cupo] == [1]
    assert resultado.por_dia == [CargaDia(fecha=lunes, cupo=1, asignados=1)]


def test_repartir_carga_exceso_de_cupo_queda_sin_cupo():
    """RN-3: nunca se supera el cupo del día; el exceso va a sin_cupo."""
    candidatos = [candidato_control_proximo(i, HOY + timedelta(days=i)) for i in range(1, 4)]
    reparto = repartir_carga(
        candidatos, HOY, HOY, [DisponibilidadDia(dia_semana=2, cupo=2)]
    )
    assert len(reparto.asignados) == 2
    assert [c.paciente_id for c in reparto.sin_cupo] == [3]
    assert reparto.por_dia == [CargaDia(fecha=HOY, cupo=2, asignados=2)]


def test_repartir_carga_reposo_se_evalua_por_dia_candidato():
    """RN-5: con reposo solo el primer día, el paciente se asigna al siguiente día sin reposo."""
    lunes = date(2026, 7, 6)
    c = candidato_con_reposo(1, lunes, lunes, PrioridadCita.CONTROL_PROXIMO)
    reparto = repartir_carga([c], lunes, lunes + timedelta(days=1), DISPONIBILIDAD_COMPLETA)
    assert [(r.paciente_id, r.fecha_candidata) for r in reparto.asignados] == [(1, HOY)]
    assert reparto.en_reposo == []
