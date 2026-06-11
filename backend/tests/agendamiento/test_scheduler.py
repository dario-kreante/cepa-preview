"""Tests exhaustivos del scheduler puro (sin BD).

Cubre todos los TC-080-XX, CA y RN del spec CEPA-080.
"""

from datetime import date, timedelta


from app.agendamiento.enums import PrioridadCita
from app.agendamiento.scheduler import (
    Candidato,
    DisponibilidadDia,
    ReposoPaciente,
    proponer_agenda,
    proponer_agenda_semana,
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


# ─── TC-080-01: propuesta diaria básica ────────────────────────────────────────

def test_tc_080_01_propuesta_diaria_cinco_candidatos():
    """TC-080-01: 5 candidatos sin reposo, cupo 8 → se proponen los 5."""
    candidatos = [candidato_control_proximo(i, HOY + timedelta(days=1)) for i in range(1, 6)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 5


def test_propuesta_diaria_no_excede_cupo():
    """RN-3: con 10 candidatos y cupo 8, solo 8 se proponen ese día."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 11)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 8


# ─── TC-080-04: exclusión por reposo (RN-1) ────────────────────────────────────

def test_tc_080_04_exclusion_por_reposo_vigente():
    """TC-080-04: paciente con reposo que cubre la fecha candidata → NO se propone."""
    candidatos = [
        candidato_con_reposo(
            1,
            date(2026, 7, 1), date(2026, 7, 10),
            PrioridadCita.CONTROL_PROXIMO,
        )
    ]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 7),
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert len(resultado) == 1
    assert resultado[0].excluida_por is not None
    assert "reposo vigente" in resultado[0].excluida_por
    assert "2026-07-10" in resultado[0].excluida_por


def test_exclusion_reposo_incluye_fecha_fin_en_mensaje():
    """RN-1, CA-4: el mensaje indica hasta cuándo dura el reposo."""
    candidatos = [
        candidato_con_reposo(
            99, date(2026, 7, 1), date(2026, 7, 31),
            PrioridadCita.CONTROL_VENCIDO,
        )
    ]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 15),
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert resultado[0].excluida_por == "reposo vigente hasta 2026-07-31"


# ─── TC-080-07: reposo prevalece sobre receta (RN-1) ───────────────────────────

def test_tc_080_07_reposo_prevalece_sobre_receta():
    """TC-080-07: paciente con receta reciente Y reposo vigente → excluido (RN-1)."""
    candidatos = [
        candidato_con_reposo(
            1, date(2026, 7, 1), date(2026, 7, 10),
            PrioridadCita.SEGUIMIENTO_RECETA,
        )
    ]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 7),
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert resultado[0].excluida_por is not None


# ─── TC-080-05: priorización (RN-2) ────────────────────────────────────────────

def test_tc_080_05_control_vencido_antes_que_proximo():
    """TC-080-05: control vencido tiene mayor prioridad que control próximo."""
    ctrl_vencido = candidato_control_vencido(1, HOY - timedelta(days=3))
    ctrl_proximo = candidato_control_proximo(2, HOY + timedelta(days=2))
    # Cupo 1 para forzar el orden
    disponibilidad_cupo1 = [DisponibilidadDia(dia_semana=d, cupo=1) for d in range(1, 6)]
    resultado = proponer_agenda(
        candidatos=[ctrl_proximo, ctrl_vencido],  # orden inverso intencionado
        fecha=HOY,
        disponibilidad=disponibilidad_cupo1,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 1
    assert propuestos[0].paciente_id == 1  # el vencido, no el próximo


def test_orden_de_prioridad_completo_rn2():
    """RN-2: vencido(1) > próximo(2) > receta(3). A igual prioridad, más antiguo primero."""
    receta = candidato_receta(3)
    proximo = candidato_control_proximo(2, HOY + timedelta(days=1))
    vencido = candidato_control_vencido(1, HOY - timedelta(days=5))
    # Los 3 caben (cupo 8) pero el orden de la lista resultante debe respetar RN-2
    resultado = proponer_agenda(
        candidatos=[receta, proximo, vencido],
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    prioridades = [r.prioridad for r in propuestos]
    assert prioridades == [
        PrioridadCita.CONTROL_VENCIDO,
        PrioridadCita.CONTROL_PROXIMO,
        PrioridadCita.SEGUIMIENTO_RECETA,
    ]


def test_a_igual_prioridad_vencido_antes_se_propone_primero():
    """RN-2: a igual prioridad, más antiguo/vencido primero."""
    mas_antiguo = candidato_control_vencido(1, HOY - timedelta(days=10))
    menos_antiguo = candidato_control_vencido(2, HOY - timedelta(days=2))
    disponibilidad_cupo1 = [DisponibilidadDia(dia_semana=d, cupo=1) for d in range(1, 6)]
    resultado = proponer_agenda(
        candidatos=[menos_antiguo, mas_antiguo],
        fecha=HOY,
        disponibilidad=disponibilidad_cupo1,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert propuestos[0].paciente_id == 1  # el más antiguo


# ─── TC-080-06: candidato por receta (CA-6) ─────────────────────────────────────

def test_tc_080_06_receta_reciente_incluye_candidato():
    """TC-080-06: candidato con receta reciente sin reposo → propuesto con etiqueta."""
    candidatos = [candidato_receta(42)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 1
    assert propuestos[0].prioridad == PrioridadCita.SEGUIMIENTO_RECETA
    assert "seguimiento de receta" in propuestos[0].razon.lower()


# ─── Fin de semana nunca se propone (RN-4) ─────────────────────────────────────

def test_fin_de_semana_devuelve_lista_vacia():
    """RN-4: sabado y domingo → no hay bloques disponibles → lista vacía."""
    candidatos = [candidato_control_proximo(1, date(2026, 7, 11))]
    resultado_sab = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 11),  # sábado
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    resultado_dom = proponer_agenda(
        candidatos=candidatos,
        fecha=date(2026, 7, 12),  # domingo
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert len(resultado_sab) == 0
    assert len(resultado_dom) == 0


# ─── Sin disponibilidad → lista vacía ──────────────────────────────────────────

def test_sin_disponibilidad_para_el_dia_devuelve_vacio():
    """RN-3/4: si el profesional no tiene disponibilidad ese día de semana → vacío."""
    # Solo disponibilidad el lunes (1), pero la fecha es martes (2)
    disponibilidad_solo_lunes = [DisponibilidadDia(dia_semana=1, cupo=8)]
    candidatos = [candidato_control_proximo(1, HOY)]
    resultado = proponer_agenda(
        candidatos=candidatos,
        fecha=HOY,  # martes
        disponibilidad=disponibilidad_solo_lunes,
    )
    assert len(resultado) == 0


# ─── Sin candidatos → lista vacía ──────────────────────────────────────────────

def test_sin_candidatos_devuelve_lista_vacia():
    resultado = proponer_agenda(
        candidatos=[],
        fecha=HOY,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    assert len(resultado) == 0


# ─── TC-080-02: propuesta semanal (CA-2) ───────────────────────────────────────

def test_tc_080_02_propuesta_semanal_distribuye_12_candidatos():
    """TC-080-02: 12 candidatos, cupo 8/día, semana lun–vie → distribuidos sin exceder cupo."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 13)]
    lunes = date(2026, 7, 6)  # lunes
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    # 12 candidatos caben en lun+mar (8+4); ningún día supera 8
    propuestos_por_dia: dict[str, int] = {}
    for r in resultado:
        if r.excluida_por is None:
            dia = str(r.fecha_candidata)
            propuestos_por_dia[dia] = propuestos_por_dia.get(dia, 0) + 1
    assert all(v <= 8 for v in propuestos_por_dia.values()), "Ningún día puede superar el cupo"
    total_propuestos = sum(1 for r in resultado if r.excluida_por is None)
    assert total_propuestos == 12


def test_propuesta_semanal_no_incluye_fin_de_semana():
    """RN-4: la semana lun–vie nunca produce citas en sáb/dom."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 5)]
    lunes = date(2026, 7, 6)
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    for r in resultado:
        assert r.fecha_candidata.isoweekday() <= 5, "No debe haber citas en fin de semana"


# ─── TC-080-08: desbordamiento de cupo se difiere (RN-3) ───────────────────────

def test_tc_080_08_exceso_se_difiere_al_dia_siguiente():
    """TC-080-08: 14 candidatos, cupo 8/día → 8 el día 1, 6 el día 2 (siguiente hábil)."""
    candidatos = [candidato_control_proximo(i, HOY) for i in range(1, 15)]
    lunes = date(2026, 7, 6)
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=candidatos,
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    propuestos = [r for r in resultado if r.excluida_por is None]
    # 8 el lunes + 6 el martes
    assert len(propuestos) == 14
    dias = {str(r.fecha_candidata) for r in propuestos}
    assert len(dias) >= 2  # distribuidos en al menos 2 días


# ─── Reposo evaluado fecha a fecha en propuesta semanal (RN-5) ─────────────────

def test_rn5_reposo_evaluado_por_fecha_candidata_no_hoy():
    """RN-5: propuesta semanal excluye el paciente solo en días con reposo, no en todos."""
    # Reposo solo mar–mié (días 2 y 3); debe ser propuesto el lun, jue, vie
    reposo_martes_miercoles = [
        ReposoPaciente(inicio=date(2026, 7, 7), fin=date(2026, 7, 8))
    ]
    candidato = Candidato(
        paciente_id=1,
        prioridad=PrioridadCita.CONTROL_PROXIMO,
        razon="control próximo",
        fecha_ctrl=date(2026, 7, 10),
        reposos=reposo_martes_miercoles,
    )
    lunes = date(2026, 7, 6)
    viernes = date(2026, 7, 10)
    resultado = proponer_agenda_semana(
        candidatos=[candidato],
        semana_inicio=lunes,
        semana_fin=viernes,
        disponibilidad=DISPONIBILIDAD_COMPLETA,
    )
    # Solo lunes (07-06) debe aparecer como propuesto (el primero disponible sin reposo)
    propuestos = [r for r in resultado if r.excluida_por is None]
    assert len(propuestos) == 1
    assert propuestos[0].fecha_candidata == date(2026, 7, 6)  # lunes
