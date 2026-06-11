from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, SmallInteger, String

from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda


def _nombres(tabla):
    return set(tabla.columns.keys())


def test_disponibilidad_prof_columnas():
    t = DisponibilidadProf.__table__
    assert t.name == "disponibilidad_prof"
    assert _nombres(t) == {
        "id", "profesional_id", "dia_semana", "cupo_diario", "activo", "created_at",
    }


def test_propuesta_agenda_columnas():
    t = PropuestaAgenda.__table__
    assert t.name == "propuesta_agenda"
    assert _nombres(t) == {
        "id", "profesional_id", "tipo", "fecha_inicio", "fecha_fin",
        "estado", "generado_por", "created_at",
    }


def test_cita_propuesta_columnas():
    t = CitaPropuesta.__table__
    assert t.name == "cita_propuesta"
    assert _nombres(t) == {
        "id", "propuesta_id", "paciente_id", "fecha_candidata",
        "prioridad", "razon", "estado", "excluida_por", "created_at",
    }


def test_portabilidad_identificadores():
    for modelo in (DisponibilidadProf, PropuestaAgenda, CitaPropuesta):
        t = modelo.__table__
        for nombre in [t.name, *t.columns.keys()]:
            assert nombre == nombre.lower(), f"{nombre} debe ser minúscula"
            assert len(nombre) <= 30, f"{nombre} supera 30 chars"


def test_pks_son_biginteger_con_identity():
    for modelo in (DisponibilidadProf, PropuestaAgenda, CitaPropuesta):
        cols = modelo.__table__.columns
        assert isinstance(cols["id"].type, BigInteger)
        assert cols["id"].identity is not None


def test_fechas_con_timezone():
    for modelo in (DisponibilidadProf, PropuestaAgenda, CitaPropuesta):
        cols = modelo.__table__.columns
        assert isinstance(cols["created_at"].type, DateTime)
        assert cols["created_at"].type.timezone is True
