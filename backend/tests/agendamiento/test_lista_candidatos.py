"""Candidatos de la lista de trabajo y detección de hora vigente en SALUTEM."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.agendamiento.salutem import pacientes_con_hora_vigente, pacientes_sin_vinculo
from app.agendamiento.service import _cargar_candidatos
from app.domain.enums import EstadoCaso
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.salutem_copia import SalutemCita, SalutemPersona

HOY = date(2026, 10, 16)
AHORA = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
PROF_ID = 301
PROF_NOMBRE = "Dra Lista"
_seq = {"n": 0}


def _n() -> int:
    _seq["n"] += 1
    return _seq["n"]


@pytest.fixture(autouse=True)
def _profesional(db_session):
    db_session.add(Profesional(id=PROF_ID, nombre=PROF_NOMBRE, origen="SIGE", activo=True))
    db_session.flush()


def _paciente(db, *, rut: str | None = None, persona_id: int | None = None) -> Paciente:
    p = Paciente(
        rut=rut, nombre="Paciente Lista", sexo="F", edad=40, region="Maule",
        salutem_persona_id=persona_id,
    )
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente: Paciente, estado: str = EstadoCaso.ACTIVO.value) -> Ingreso:
    n = _n()
    i = Ingreso(
        paciente_id=paciente.id, folio=f"F-LISTA-{n}", folio_manual=True,
        fecha_ingreso=date(2026, 1, 1), tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="test lista", estado=estado,
    )
    db.add(i)
    db.flush()
    return i


def _control(db, ingreso: Ingreso, *, origen: str, agendado: bool, proximo: date) -> ControlMedico:
    c = ControlMedico(
        ingreso_id=ingreso.id, fecha_control=date(2026, 9, 1), semana_control=1,
        medico_tratante=PROF_NOMBRE, region_derivacion="Maule", proximo_control=proximo,
        proximo_agendado=agendado, tiene_licencia=False, origen=origen,
    )
    db.add(c)
    db.flush()
    return c


def _persona(db, *, salutem_id: int, rut: str | None) -> SalutemPersona:
    p = SalutemPersona(
        salutem_id=salutem_id, rut=rut, contenido={}, hash_contenido="h",
        visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
    )
    db.add(p)
    db.flush()
    return p


def _cita(db, persona_id: int, fecha: date, estado=EstadoCitaSalutem.AGENDADO, desaparecida=None):
    c = SalutemCita(
        cita_id=_n() + 700000, persona_id=persona_id, fecha_cita=fecha, estado_id=int(estado),
        contenido={}, hash_contenido="h", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
        cambiado_en=AHORA, desaparecida_en=desaparecida,
    )
    db.add(c)
    db.flush()
    return c


def test_hora_vigente_por_rut_sin_persona_id(db_session):
    p = _paciente(db_session, rut="111111111")
    _persona(db_session, salutem_id=8101, rut="111111111")
    _cita(db_session, 8101, HOY + timedelta(days=1))
    assert pacientes_con_hora_vigente(db_session, [p.id], HOY) == {p.id}


def test_hora_vigente_por_persona_id(db_session):
    p = _paciente(db_session, rut=None, persona_id=8102)
    _persona(db_session, salutem_id=8102, rut=None)
    _cita(db_session, 8102, HOY + timedelta(days=1))
    assert pacientes_con_hora_vigente(db_session, [p.id], HOY) == {p.id}


def test_cita_anulada_o_no_asiste_no_cuenta(db_session):
    p = _paciente(db_session, rut="222222222")
    _persona(db_session, salutem_id=8103, rut="222222222")
    manana = HOY + timedelta(days=1)
    _cita(db_session, 8103, manana, EstadoCitaSalutem.ANULADO)
    _cita(db_session, 8103, manana, EstadoCitaSalutem.NO_ASISTE)
    _cita(db_session, 8103, manana, EstadoCitaSalutem.AGENDADO, desaparecida=AHORA)
    assert pacientes_con_hora_vigente(db_session, [p.id], HOY) == set()


def test_cita_pasada_no_cuenta(db_session):
    p = _paciente(db_session, rut="333333333")
    _persona(db_session, salutem_id=8104, rut="333333333")
    _cita(db_session, 8104, HOY - timedelta(days=1))
    assert pacientes_con_hora_vigente(db_session, [p.id], HOY) == set()


def test_cita_de_hoy_cuenta(db_session):
    p = _paciente(db_session, rut="333333334")
    _persona(db_session, salutem_id=8105, rut="333333334")
    _cita(db_session, 8105, HOY)
    assert pacientes_con_hora_vigente(db_session, [p.id], HOY) == {p.id}


def test_sin_vinculo(db_session):
    sin = _paciente(db_session, rut="444444444")
    con = _paciente(db_session, rut="555555555")
    _persona(db_session, salutem_id=8106, rut="555555555")
    assert pacientes_sin_vinculo(db_session, [sin.id, con.id]) == {sin.id}


def test_listas_vacias(db_session):
    assert pacientes_con_hora_vigente(db_session, [], HOY) == set()
    assert pacientes_sin_vinculo(db_session, []) == set()


def _candidatos(db):
    return _cargar_candidatos(db, PROF_ID, HOY, HOY + timedelta(days=6), HOY)


def test_candidatos_ignoran_proximo_agendado_en_controles_salutem(db_session):
    p = _paciente(db_session, rut="666666666")
    _control(db_session, _ingreso(db_session, p), origen="SALUTEM", agendado=True,
             proximo=HOY - timedelta(days=3))
    assert [c.paciente_id for c in _candidatos(db_session)] == [p.id]


def test_candidatos_respetan_proximo_agendado_en_controles_cepa(db_session):
    p = _paciente(db_session, rut="777777777")
    _control(db_session, _ingreso(db_session, p), origen="CEPA", agendado=True,
             proximo=HOY - timedelta(days=3))
    assert _candidatos(db_session) == []


@pytest.mark.parametrize("estado", [EstadoCaso.CERRADO.value, EstadoCaso.DERIVADO.value])
def test_candidatos_solo_ingreso_activo(db_session, estado):
    p = _paciente(db_session, rut="888888888")
    _control(db_session, _ingreso(db_session, p, estado), origen="CEPA", agendado=False,
             proximo=HOY - timedelta(days=3))
    assert _candidatos(db_session) == []
