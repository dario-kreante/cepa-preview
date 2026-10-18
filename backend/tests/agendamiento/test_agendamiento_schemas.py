import pytest
from datetime import date
from pydantic import ValidationError

from app.agendamiento.enums import DiaSemana, TipoPropuesta
from app.agendamiento.schemas import (
    DisponibilidadProfCreate,
    PropuestaAgendaRead,
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
