"""Tests de integración del servicio de agendamiento (con BD real via db_session).

Adaptaciones respecto al plan original (Deviación 5-7):
- La tabla 'control_medico' (no 'control') tiene columnas ingreso_id, proximo_control,
  medico_tratante (no paciente_id/profesional_id/fecha_prox_control).
  Los tests insertan en control_medico con un ingreso de prueba.
- La tabla 'licencia_medica' (no 'licencia') tiene inicio_reposo/fin_reposo y se enlaza
  por ingreso_id, no directamente por paciente_id.
- La tabla 'receta' no tiene requiere_seguimiento/gestionada; el seguimiento se detecta
  por fecha_revision futura.
"""

from datetime import date, timedelta

import pytest

from app.agendamiento.enums import EstadoCita, EstadoPropuesta, PrioridadCita, TipoPropuesta
from app.agendamiento.models import CitaPropuesta, DisponibilidadProf
from app.agendamiento.schemas import GenerarPropuestaRequest
from app.agendamiento.service import (
    confirmar_citas,
    crear_disponibilidad,
    generar_propuesta,
    obtener_propuesta,
)

HOY = date(2026, 7, 7)  # martes
PROF_ID = 101
PROF_NOMBRE = "Dr Test"
PACIENTE_ID = 201


@pytest.fixture(autouse=True)
def _profesional(db_session):
    """Da de alta PROF_ID en el catálogo: los candidatos se cruzan por su nombre."""
    from app.models.profesional import Profesional
    db_session.add(Profesional(id=PROF_ID, nombre=PROF_NOMBRE, origen="SIGE", activo=True))
    db_session.flush()


def _insertar_disponibilidad_completa(db):
    for dia in range(1, 6):
        db.add(DisponibilidadProf(
            profesional_id=PROF_ID, dia_semana=dia, cupo_diario=8, activo=True,
        ))
    db.flush()


def _crear_paciente_e_ingreso(db, rut: str = "11222333-9"):
    """Crea un paciente e ingreso de prueba; retorna (paciente, ingreso)."""
    from app.models.paciente import Paciente
    from app.models.ingreso import Ingreso
    paciente = Paciente(
        rut=rut, nombre="Test Agenda", sexo="M", edad=40, region="Metropolitana"
    )
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio=f"F-AGENDA-{rut[:4]}",
        folio_manual=True,
        fecha_ingreso=date(2026, 1, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Test agendamiento",
        estado="activo",
    )
    db.add(ingreso)
    db.flush()
    return paciente, ingreso


def _insertar_control_proximo(db, ingreso_id: int, fecha: date, medico: str = PROF_NOMBRE):
    """Inserta un control médico con próximo control en la fecha dada (Desviación 5)."""
    from app.models.control_medico import ControlMedico
    ctrl = ControlMedico(
        ingreso_id=ingreso_id,
        fecha_control=date(2026, 1, 15),
        semana_control=1,
        medico_tratante=medico,
        region_derivacion="Metropolitana",
        proximo_control=fecha,
        proximo_agendado=False,
        tiene_licencia=False,
    )
    db.add(ctrl)
    db.flush()


def test_crear_disponibilidad(db_session):
    dp = crear_disponibilidad(
        db=db_session,
        profesional_id=PROF_ID,
        dia_semana=1,
        cupo_diario=6,
        actor="admin_test",
    )
    assert dp.id is not None
    assert dp.cupo_diario == 6
    assert dp.activo is True


def test_generar_propuesta_diaria_sin_candidatos(db_session):
    _insertar_disponibilidad_completa(db_session)
    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(
        db=db_session,
        req=req,
        actor="admin_test",
    )
    assert propuesta.id is not None
    assert propuesta.tipo == TipoPropuesta.DIARIA.value
    assert propuesta.estado == EstadoPropuesta.BORRADOR.value
    # Sin candidatos, la propuesta queda vacía
    citas = db_session.query(CitaPropuesta).filter_by(propuesta_id=propuesta.id).all()
    assert len(citas) == 0


def test_generar_propuesta_diaria_con_candidatos(db_session):
    """Integración: genera propuesta con candidatos de control próximo."""
    _insertar_disponibilidad_completa(db_session)
    # Pre-poblar control próximo via control_medico (Desviación 5)
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="11222333-9")
    _insertar_control_proximo(db_session, ingreso.id, HOY + timedelta(days=2))

    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(db=db_session, req=req, actor="admin_test")
    citas = db_session.query(CitaPropuesta).filter_by(propuesta_id=propuesta.id).all()
    assert len(citas) >= 1
    assert citas[0].estado == EstadoCita.PROPUESTA.value


def test_confirmar_citas_cambia_estado(db_session):
    """CA-7: confirmar citas propuestas las marca como confirmadas."""
    _insertar_disponibilidad_completa(db_session)
    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(db=db_session, req=req, actor="admin_test")
    # Insertar manualmente una cita propuesta para confirmar
    cita = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=PACIENTE_ID,
        fecha_candidata=HOY,
        prioridad=PrioridadCita.CONTROL_PROXIMO.value,
        razon="control próximo",
        estado=EstadoCita.PROPUESTA.value,
    )
    db_session.add(cita)
    db_session.flush()

    confirmadas = confirmar_citas(
        db=db_session,
        propuesta_id=propuesta.id,
        cita_ids=[cita.id],
        actor="admin_test",
    )
    assert len(confirmadas) == 1
    assert confirmadas[0].estado == EstadoCita.CONFIRMADA.value


def test_confirmar_citas_estado_propuesta_pasa_a_confirmada(db_session):
    """CA-7: cuando al menos una cita se confirma, la propuesta cambia a 'confirmada'."""
    _insertar_disponibilidad_completa(db_session)
    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(db=db_session, req=req, actor="admin_test")
    cita = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=PACIENTE_ID,
        fecha_candidata=HOY,
        prioridad=PrioridadCita.CONTROL_PROXIMO.value,
        razon="control próximo",
        estado=EstadoCita.PROPUESTA.value,
    )
    db_session.add(cita)
    db_session.flush()

    confirmar_citas(db=db_session, propuesta_id=propuesta.id, cita_ids=[cita.id], actor="admin_test")
    db_session.refresh(propuesta)
    assert propuesta.estado == EstadoPropuesta.CONFIRMADA.value


def test_obtener_propuesta_inexistente_retorna_none(db_session):
    assert obtener_propuesta(db=db_session, propuesta_id=99999) is None


# ─── Fix 1: citas excluidas no confirmables (RN-1) ────────────────────────────

def test_confirmar_cita_excluida_no_cambia_estado(db_session):
    """RN-1: una cita con excluida_por != None no puede ser confirmada,
    aunque su estado sea 'propuesta'."""
    _insertar_disponibilidad_completa(db_session)
    req = GenerarPropuestaRequest(
        profesional_id=PROF_ID,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=HOY,
    )
    propuesta = generar_propuesta(db=db_session, req=req, actor="admin_test")

    cita_excluida = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=PACIENTE_ID,
        fecha_candidata=HOY,
        prioridad=PrioridadCita.CONTROL_PROXIMO.value,
        razon="control próximo",
        estado=EstadoCita.PROPUESTA.value,
        excluida_por="reposo vigente hasta 2026-07-20",
    )
    db_session.add(cita_excluida)
    db_session.flush()

    confirmadas = confirmar_citas(
        db=db_session,
        propuesta_id=propuesta.id,
        cita_ids=[cita_excluida.id],
        actor="admin_test",
    )
    # La cita excluida NO debe aparecer como confirmada
    assert confirmadas == []
    db_session.refresh(cita_excluida)
    assert cita_excluida.estado == EstadoCita.PROPUESTA.value


# ─── Fix 2: último control por ingreso + proximo_agendado (Desviación 5) ──────

def _insertar_control_medico(
    db,
    ingreso_id: int,
    fecha_control: date,
    proximo_control: date | None = None,
    proximo_agendado: bool = False,
    medico: str = PROF_NOMBRE,
):
    """Inserta un control_medico con los campos dados."""
    from app.models.control_medico import ControlMedico
    ctrl = ControlMedico(
        ingreso_id=ingreso_id,
        fecha_control=fecha_control,
        semana_control=1,
        medico_tratante=medico,
        region_derivacion="Metropolitana",
        proximo_control=proximo_control,
        proximo_agendado=proximo_agendado,
        tiene_licencia=False,
    )
    db.add(ctrl)
    db.flush()
    return ctrl


def test_control_stale_no_genera_candidato_si_hay_control_futuro(db_session):
    """Fix 2a: un ingreso con control vencido antiguo + control reciente con fecha futura
    NO debe aparecer como CONTROL_VENCIDO; solo aplica el último control.
    Usa date.today() porque _cargar_candidatos llama date.today() internamente.
    """
    from datetime import date as _date
    from app.agendamiento.service import _cargar_candidatos
    from app.agendamiento.enums import PrioridadCita

    hoy_real = _date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="55500001-1")

    # Control viejo vencido (fecha_control = hace ~120 días, proximo_control vencido)
    _insertar_control_medico(
        db_session, ingreso.id,
        fecha_control=hoy_real - timedelta(days=120),
        proximo_control=hoy_real - timedelta(days=90),  # vencido
    )
    # Control reciente con proximo_control en el futuro
    _insertar_control_medico(
        db_session, ingreso.id,
        fecha_control=hoy_real - timedelta(days=5),
        proximo_control=hoy_real + timedelta(days=60),  # futuro — no vencido
    )

    candidatos = _cargar_candidatos(
        db_session,
        profesional_id=PROF_ID,
        fecha_ini=hoy_real,
        fecha_fin=hoy_real + timedelta(days=6),
    )
    pids_vencidos = [
        c.paciente_id for c in candidatos
        if c.prioridad == PrioridadCita.CONTROL_VENCIDO
        and c.paciente_id == ingreso.paciente_id
    ]
    assert pids_vencidos == [], (
        "El paciente con control reciente futuro no debe aparecer como CONTROL_VENCIDO"
    )


def test_control_proximo_agendado_no_genera_candidato(db_session):
    """Fix 2b: un control con proximo_agendado=True no debe generar propuesta.
    Usa date.today() para alinear con _cargar_candidatos.
    """
    from datetime import date as _date
    from app.agendamiento.service import _cargar_candidatos

    hoy_real = _date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="55500002-2")
    _insertar_control_medico(
        db_session, ingreso.id,
        fecha_control=hoy_real - timedelta(days=5),
        proximo_control=hoy_real + timedelta(days=3),  # dentro del horizonte
        proximo_agendado=True,  # ya tiene cita — no reproponer
    )

    candidatos = _cargar_candidatos(
        db_session,
        profesional_id=PROF_ID,
        fecha_ini=hoy_real,
        fecha_fin=hoy_real + timedelta(days=6),
    )
    pids = [c.paciente_id for c in candidatos if c.paciente_id == ingreso.paciente_id]
    assert pids == [], "proximo_agendado=True no debe generar candidato"


# ─── Fix 3: ventana receta acotada + fecha_envio IS NULL (RN-6) ───────────────

def _insertar_receta(
    db,
    ingreso_id: int,
    fecha_revision: date,
    fecha_envio: date | None = None,
    medico: str = PROF_NOMBRE,
):
    """Inserta paciente→ingreso→reg_farmacologico→receta para tests de Fix 3."""
    from app.models.farmacos import RegistroFarmacologico, Receta
    rf = RegistroFarmacologico(
        ingreso_id=ingreso_id,
        medico_tratante=medico,
        estado_farmacologico="activo",
        activo=True,
    )
    db.add(rf)
    db.flush()
    receta = Receta(
        registro_id=rf.id,
        fecha_emision=date(2026, 6, 1),
        fecha_revision=fecha_revision,
        fecha_envio=fecha_envio,
        marca_medicamento="TestMarca",
    )
    db.add(receta)
    db.flush()


def test_receta_fuera_de_ventana_no_genera_candidato(db_session):
    """Fix 3: receta con fecha_revision más allá de hoy + VENTANA no debe generar candidato.
    Usa date.today() porque _cargar_candidatos llama date.today() internamente.
    """
    from datetime import date as _date
    from app.agendamiento.service import _cargar_candidatos, VENTANA_SEGUIMIENTO_RECETA_DIAS
    from app.agendamiento.enums import PrioridadCita

    hoy_real = _date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="77700001-1")
    fecha_fuera = hoy_real + timedelta(days=VENTANA_SEGUIMIENTO_RECETA_DIAS + 5)
    _insertar_receta(db_session, ingreso.id, fecha_revision=fecha_fuera)

    candidatos = _cargar_candidatos(
        db_session,
        profesional_id=PROF_ID,
        fecha_ini=hoy_real,
        fecha_fin=hoy_real + timedelta(days=6),
    )
    pids = [
        c.paciente_id for c in candidatos
        if c.prioridad == PrioridadCita.SEGUIMIENTO_RECETA
        and c.paciente_id == ingreso.paciente_id
    ]
    assert pids == [], "Receta fuera de ventana RN-6 no debe generar candidato"


def test_receta_gestionada_no_genera_candidato(db_session):
    """Fix 3: receta con fecha_envio != NULL (ya gestionada) no debe generar candidato — RN-6.
    Usa date.today() para alinear con _cargar_candidatos.
    """
    from datetime import date as _date
    from app.agendamiento.service import _cargar_candidatos
    from app.agendamiento.enums import PrioridadCita

    hoy_real = _date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="77700002-2")
    _insertar_receta(
        db_session, ingreso.id,
        fecha_revision=hoy_real + timedelta(days=5),
        fecha_envio=hoy_real - timedelta(days=1),  # ya fue despachada
    )

    candidatos = _cargar_candidatos(
        db_session,
        profesional_id=PROF_ID,
        fecha_ini=hoy_real,
        fecha_fin=hoy_real + timedelta(days=6),
    )
    pids = [
        c.paciente_id for c in candidatos
        if c.prioridad == PrioridadCita.SEGUIMIENTO_RECETA
        and c.paciente_id == ingreso.paciente_id
    ]
    assert pids == [], "Receta con fecha_envio (gestionada) no debe generar candidato (RN-6)"


def test_receta_dentro_de_ventana_genera_candidato(db_session):
    """Fix 3: receta con fecha_revision en ventana y sin fecha_envio SÍ genera candidato.
    Usa date.today() para alinear con _cargar_candidatos.
    """
    from datetime import date as _date
    from app.agendamiento.service import _cargar_candidatos
    from app.agendamiento.enums import PrioridadCita

    hoy_real = _date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="77700003-3")
    _insertar_receta(
        db_session, ingreso.id,
        fecha_revision=hoy_real + timedelta(days=10),  # dentro de la ventana (30 días)
        fecha_envio=None,
    )

    candidatos = _cargar_candidatos(
        db_session,
        profesional_id=PROF_ID,
        fecha_ini=hoy_real,
        fecha_fin=hoy_real + timedelta(days=6),
    )
    pids = [
        c.paciente_id for c in candidatos
        if c.prioridad == PrioridadCita.SEGUIMIENTO_RECETA
        and c.paciente_id == ingreso.paciente_id
    ]
    assert pids == [ingreso.paciente_id], "Receta válida dentro de ventana debe generar candidato"


# ─── Candidatos por profesional (cruce por medico_tratante) ───────────────────

def _candidatos_hoy(db, profesional_id: int = PROF_ID):
    from app.agendamiento.service import _cargar_candidatos
    hoy_real = date.today()
    return _cargar_candidatos(
        db, profesional_id=profesional_id,
        fecha_ini=hoy_real, fecha_fin=hoy_real + timedelta(days=6),
    )


def test_candidatos_solo_del_profesional_elegido(db_session):
    """Controles vencidos, próximos y recetas de otro médico no entran en la propuesta."""
    hoy_real = date.today()
    _, ing_vencido = _crear_paciente_e_ingreso(db_session, rut="88800001-1")
    _insertar_control_medico(
        db_session, ing_vencido.id, fecha_control=hoy_real - timedelta(days=40),
        proximo_control=hoy_real - timedelta(days=10),
    )
    _, ing_proximo = _crear_paciente_e_ingreso(db_session, rut="88800002-2")
    _insertar_control_proximo(db_session, ing_proximo.id, hoy_real + timedelta(days=2))
    _, ing_receta = _crear_paciente_e_ingreso(db_session, rut="88800003-3")
    _insertar_receta(db_session, ing_receta.id, fecha_revision=hoy_real + timedelta(days=5))

    _, otro_vencido = _crear_paciente_e_ingreso(db_session, rut="88800004-4")
    _insertar_control_medico(
        db_session, otro_vencido.id, fecha_control=hoy_real - timedelta(days=40),
        proximo_control=hoy_real - timedelta(days=10), medico="Dra Otra",
    )
    _, otro_proximo = _crear_paciente_e_ingreso(db_session, rut="88800005-5")
    _insertar_control_proximo(
        db_session, otro_proximo.id, hoy_real + timedelta(days=2), medico="Dra Otra"
    )
    _, otra_receta = _crear_paciente_e_ingreso(db_session, rut="88800006-6")
    _insertar_receta(
        db_session, otra_receta.id, fecha_revision=hoy_real + timedelta(days=5),
        medico="Dra Otra",
    )

    por_paciente = {c.paciente_id: c.prioridad for c in _candidatos_hoy(db_session)}

    assert por_paciente == {
        ing_vencido.paciente_id: PrioridadCita.CONTROL_VENCIDO,
        ing_proximo.paciente_id: PrioridadCita.CONTROL_PROXIMO,
        ing_receta.paciente_id: PrioridadCita.SEGUIMIENTO_RECETA,
    }


def test_candidatos_usan_medico_del_ultimo_control(db_session):
    """Si el paciente cambió de médico, cuenta el del último control, no el histórico."""
    from app.models.profesional import Profesional

    hoy_real = date.today()
    otra = Profesional(nombre="Dra Otra", origen="SIGE", activo=True)
    db_session.add(otra)
    db_session.flush()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="88800007-7")
    _insertar_control_medico(
        db_session, ingreso.id, fecha_control=hoy_real - timedelta(days=60),
        proximo_control=hoy_real - timedelta(days=30),
    )
    _insertar_control_medico(
        db_session, ingreso.id, fecha_control=hoy_real - timedelta(days=5),
        proximo_control=hoy_real + timedelta(days=2), medico="Dra Otra",
    )

    assert [c.paciente_id for c in _candidatos_hoy(db_session)] == []
    assert [c.paciente_id for c in _candidatos_hoy(db_session, otra.id)] == [
        ingreso.paciente_id
    ]


def test_candidatos_toleran_espacios_en_medico_tratante(db_session):
    """El catálogo guarda el nombre recortado; el texto del control puede traer espacios."""
    hoy_real = date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="88800008-8")
    _insertar_control_proximo(
        db_session, ingreso.id, hoy_real + timedelta(days=2), medico=f"  {PROF_NOMBRE} "
    )

    assert [c.paciente_id for c in _candidatos_hoy(db_session)] == [ingreso.paciente_id]


def test_profesional_inexistente_no_tiene_candidatos(db_session):
    hoy_real = date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="88800009-9")
    _insertar_control_proximo(db_session, ingreso.id, hoy_real + timedelta(days=2))

    assert _candidatos_hoy(db_session, profesional_id=987654) == []


# ─── Confirmar marca proximo_agendado ──────────────────────────────────────────

def _propuesta_con_cita(db, paciente_id: int, prioridad: PrioridadCita):
    _insertar_disponibilidad_completa(db)
    propuesta = generar_propuesta(
        db=db,
        req=GenerarPropuestaRequest(
            profesional_id=PROF_ID, tipo=TipoPropuesta.DIARIA, fecha_inicio=HOY,
        ),
        actor="admin_test",
    )
    cita = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=paciente_id,
        fecha_candidata=HOY,
        prioridad=prioridad.value,
        razon="test",
        estado=EstadoCita.PROPUESTA.value,
    )
    db.add(cita)
    db.flush()
    return propuesta, cita


def test_confirmar_cita_de_control_marca_proximo_agendado_del_ultimo_control(db_session):
    hoy_real = date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="99900001-1")
    viejo = _insertar_control_medico(
        db_session, ingreso.id, fecha_control=hoy_real - timedelta(days=60),
        proximo_control=hoy_real - timedelta(days=30),
    )
    ultimo = _insertar_control_medico(
        db_session, ingreso.id, fecha_control=hoy_real - timedelta(days=5),
        proximo_control=hoy_real + timedelta(days=2),
    )
    assert [c.paciente_id for c in _candidatos_hoy(db_session)] == [ingreso.paciente_id]

    propuesta, cita = _propuesta_con_cita(
        db_session, ingreso.paciente_id, PrioridadCita.CONTROL_PROXIMO
    )
    confirmar_citas(db_session, propuesta.id, [cita.id], actor="admin_test")

    db_session.refresh(ultimo)
    db_session.refresh(viejo)
    assert ultimo.proximo_agendado is True
    assert viejo.proximo_agendado is False
    # Ya no se vuelve a proponer.
    assert _candidatos_hoy(db_session) == []


def test_confirmar_cita_de_receta_no_marca_proximo_agendado(db_session):
    hoy_real = date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="99900002-2")
    ctrl = _insertar_control_medico(
        db_session, ingreso.id, fecha_control=hoy_real - timedelta(days=5),
        proximo_control=hoy_real + timedelta(days=60),
    )

    propuesta, cita = _propuesta_con_cita(
        db_session, ingreso.paciente_id, PrioridadCita.SEGUIMIENTO_RECETA
    )
    confirmar_citas(db_session, propuesta.id, [cita.id], actor="admin_test")

    db_session.refresh(ctrl)
    assert ctrl.proximo_agendado is False


def test_confirmar_cita_excluida_no_marca_proximo_agendado(db_session):
    hoy_real = date.today()
    _, ingreso = _crear_paciente_e_ingreso(db_session, rut="99900003-3")
    ctrl = _insertar_control_medico(
        db_session, ingreso.id, fecha_control=hoy_real - timedelta(days=5),
        proximo_control=hoy_real + timedelta(days=2),
    )
    propuesta, cita = _propuesta_con_cita(
        db_session, ingreso.paciente_id, PrioridadCita.CONTROL_PROXIMO
    )
    cita.excluida_por = "reposo vigente"
    db_session.flush()

    confirmar_citas(db_session, propuesta.id, [cita.id], actor="admin_test")

    db_session.refresh(ctrl)
    assert ctrl.proximo_agendado is False
