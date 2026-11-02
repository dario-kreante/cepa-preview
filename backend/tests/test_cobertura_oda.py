"""Cobertura de la ODA (reunión 29-10, D9): controles y citas fuera de la vigencia de la ODA."""

from datetime import date, timedelta

from sqlalchemy import select

from app.domain.enums import EstadoCaso
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import AlertaNotif
from app.models.cita import Cita
from app.models.control_medico import ControlMedico
from app.models.oda import Oda
from app.services.alertas import ejecutar_job_alertas
from app.services.cobertura_oda import oda_que_cubre
from app.services.control_medico import leer_controles
from tests.test_alertas_citas import _ingreso, _paciente

HOY = date(2026, 10, 30)
_seq = {"n": 0}


def _sid() -> int:
    _seq["n"] += 1
    return 950000 + _seq["n"]


def _oda(db, ingreso, inicio, fin, ident="ODA-1") -> Oda:
    o = Oda(ingreso_id=ingreso.id, identificador=ident, fecha_registro=inicio, fecha_vencimiento=fin)
    db.add(o)
    db.flush()
    return o


def _cita(db, ingreso, fecha, estado="agendada") -> Cita:
    c = Cita(ingreso_id=ingreso.id, estado=estado, fecha=fecha, salutem_cita_id=_sid(), origen="SALUTEM")
    db.add(c)
    db.flush()
    return c


def _alertas(db) -> list[AlertaNotif]:
    return list(db.scalars(select(AlertaNotif).where(AlertaNotif.tipo == TipoAlerta.CITA_FUERA_DE_ODA.value)))


def test_oda_que_cubre_respeta_inicio_y_fin():
    a = Oda(id=1, identificador="A", fecha_registro=date(2026, 10, 1), fecha_vencimiento=date(2026, 10, 31))
    b = Oda(id=2, identificador="B", fecha_registro=None, fecha_vencimiento=date(2026, 9, 30))
    assert oda_que_cubre([a, b], date(2026, 10, 28)) is a
    assert oda_que_cubre([a, b], date(2026, 9, 15)) is b  # sin inicio: cubre hasta su fin
    assert oda_que_cubre([a, b], date(2026, 11, 1)) is None


def test_cita_agendada_fuera_de_la_oda_alerta_una_sola_vez(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000041"))
    _oda(db_session, ing, date(2026, 10, 1), date(2026, 10, 31))
    cubierta = _cita(db_session, ing, HOY + timedelta(days=1))
    fuera = _cita(db_session, ing, date(2026, 11, 5))

    ejecutar_job_alertas(db_session, hoy=HOY)
    ejecutar_job_alertas(db_session, hoy=HOY)

    (a,) = _alertas(db_session)
    assert (a.caso_tipo, a.caso_id) == ("salutem_cita", fuera.salutem_cita_id)
    assert a.caso_id != cubierta.salutem_cita_id


def test_sin_oda_registrada_ni_ingreso_inactivo_no_alerta(db_session):
    sin_oda = _ingreso(db_session, _paciente(db_session, "10000042"))
    _cita(db_session, sin_oda, HOY + timedelta(days=2))
    cerrado = _ingreso(db_session, _paciente(db_session, "10000043"), estado=EstadoCaso.CERRADO.value)
    _oda(db_session, cerrado, date(2026, 9, 1), date(2026, 9, 30))
    _cita(db_session, cerrado, HOY + timedelta(days=2))

    ejecutar_job_alertas(db_session, hoy=HOY)

    assert _alertas(db_session) == []


def test_cargar_una_oda_que_cubre_resuelve_la_alerta(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000044"))
    _oda(db_session, ing, date(2026, 10, 1), date(2026, 10, 31))
    _cita(db_session, ing, date(2026, 11, 10))
    ejecutar_job_alertas(db_session, hoy=HOY)
    (a,) = _alertas(db_session)
    assert a.estado == EstadoAlerta.PENDIENTE.value

    _oda(db_session, ing, date(2026, 11, 1), date(2026, 11, 30), ident="ODA-2")
    ejecutar_job_alertas(db_session, hoy=HOY + timedelta(days=1))

    (a,) = _alertas(db_session)
    assert a.estado == EstadoAlerta.RESUELTA.value


def test_la_lectura_del_control_dice_que_oda_lo_cubre(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000045"))
    _oda(db_session, ing, date(2026, 10, 1), date(2026, 10, 31), ident="ODA-OCT")
    controles = []
    for fecha in (date(2026, 10, 20), date(2026, 11, 3)):
        c = ControlMedico(
            ingreso_id=ing.id, fecha_control=fecha, semana_control=1, medico_tratante="Dra",
            region_derivacion="Maule", tiene_licencia=False,
        )
        db_session.add(c)
        controles.append(c)
    sin_oda = _ingreso(db_session, _paciente(db_session, "10000046"))
    c3 = ControlMedico(
        ingreso_id=sin_oda.id, fecha_control=date(2026, 10, 20), semana_control=1,
        medico_tratante="Dra", region_derivacion="Maule", tiene_licencia=False,
    )
    db_session.add(c3)
    db_session.flush()

    dentro, fuera, desconocido = leer_controles(db_session, [*controles, c3])

    assert (dentro.oda_que_cubre, dentro.fuera_de_oda) == ("ODA-OCT", False)
    assert (fuera.oda_que_cubre, fuera.fuera_de_oda) == (None, True)
    assert (desconocido.oda_que_cubre, desconocido.fuera_de_oda) == (None, False)
