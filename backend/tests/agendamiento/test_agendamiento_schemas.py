import pytest
from datetime import date
from pydantic import ValidationError

from app.agendamiento.enums import DiaSemana, EstadoCita, PrioridadCita, TipoPropuesta
from app.agendamiento.schemas import (
    CitaPropuestaRead,
    DisponibilidadProfCreate,
    DisponibilidadProfRead,
    GenerarPropuestaRequest,
    PropuestaAgendaRead,
    ConfirmarCitasRequest,
)


def test_disponibilidad_prof_create_valida():
    d = DisponibilidadProfCreate(profesional_id=1, dia_semana=DiaSemana.LUNES, cupo_diario=8)
    assert d.dia_semana == DiaSemana.LUNES
    assert d.cupo_diario == 8


def test_disponibilidad_prof_create_rechaza_fin_de_semana():
    with pytest.raises(ValidationError):
        DisponibilidadProfCreate(profesional_id=1, dia_semana=6, cupo_diario=5)


def test_disponibilidad_prof_create_rechaza_cupo_cero():
    with pytest.raises(ValidationError):
        DisponibilidadProfCreate(profesional_id=1, dia_semana=DiaSemana.MARTES, cupo_diario=0)


def test_generar_propuesta_request_diaria():
    req = GenerarPropuestaRequest(
        profesional_id=1,
        tipo=TipoPropuesta.DIARIA,
        fecha_inicio=date(2026, 7, 7),
    )
    assert req.fecha_fin == date(2026, 7, 7)


def test_generar_propuesta_request_semanal_calcula_fecha_fin():
    # 2026-07-06 es lunes (isoweekday=1); viernes de esa semana = 2026-07-10
    req = GenerarPropuestaRequest(
        profesional_id=1,
        tipo=TipoPropuesta.SEMANAL,
        fecha_inicio=date(2026, 7, 6),  # lunes
    )
    assert req.fecha_fin == date(2026, 7, 10)  # viernes de la misma semana


def test_generar_propuesta_request_mensual_calcula_fecha_fin():
    req = GenerarPropuestaRequest(
        profesional_id=1,
        tipo=TipoPropuesta.MENSUAL,
        fecha_inicio=date(2026, 7, 1),
    )
    assert req.fecha_fin == date(2026, 7, 31)


def test_generar_propuesta_request_rechaza_fin_de_semana_como_inicio():
    with pytest.raises(ValidationError):
        GenerarPropuestaRequest(
            profesional_id=1,
            tipo=TipoPropuesta.DIARIA,
            fecha_inicio=date(2026, 7, 11),  # sábado
        )


def test_confirmar_citas_request_requiere_al_menos_una():
    with pytest.raises(ValidationError):
        ConfirmarCitasRequest(cita_ids=[])


def test_propuesta_agenda_read_from_attributes():
    from datetime import datetime, timezone
    from app.agendamiento.models import PropuestaAgenda
    obj = PropuestaAgenda(
        id=1, profesional_id=2, tipo="diaria",
        fecha_inicio=date(2026, 7, 7), fecha_fin=date(2026, 7, 7),
        estado="borrador", generado_por="ana.silva",
        created_at=datetime.now(timezone.utc),
    )
    r = PropuestaAgendaRead.model_validate(obj)
    assert r.id == 1
    assert r.tipo == TipoPropuesta.DIARIA
