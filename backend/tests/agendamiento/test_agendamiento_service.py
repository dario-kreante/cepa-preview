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
from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda
from app.agendamiento.schemas import GenerarPropuestaRequest
from app.agendamiento.service import (
    confirmar_citas,
    crear_disponibilidad,
    generar_propuesta,
    obtener_propuesta,
)

HOY = date(2026, 7, 7)  # martes
PROF_ID = 101
PACIENTE_ID = 201


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


def _insertar_control_proximo(db, ingreso_id: int, fecha: date):
    """Inserta un control médico con próximo control en la fecha dada (Desviación 5)."""
    from sqlalchemy import text
    db.execute(text(
        "INSERT INTO control_medico "
        "(ingreso_id, fecha_control, semana_control, medico_tratante, region_derivacion, "
        " proximo_control, proximo_agendado, tiene_licencia, created_at, updated_at) "
        "VALUES (:iid, :fc, 1, 'Dr Test', 'Metropolitana', :prox, false, false, now(), now())"
    ), {"iid": ingreso_id, "fc": date(2026, 1, 15), "prox": fecha})
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
