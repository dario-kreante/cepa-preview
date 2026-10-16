from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.profesional import SIN_PROFESIONAL_SALUTEM, Profesional
from app.models.salutem_copia import SalutemCita, SalutemPersona
from app.services.salutem_sync.citas_cepa import ACTOR, estado_cita, sincronizar_citas
from tests.salutem_sync.conftest import AHORA

RUT = "123456785"
FECHA = date(2026, 5, 10)
_seq = {"n": 0}


def _n() -> int:
    _seq["n"] += 1
    return _seq["n"]


def _paciente(db, *, rut=RUT, persona_id=None) -> Paciente:
    p = Paciente(
        rut=rut, nombre="Paciente Citas", sexo="F", edad=40, region="Maule",
        salutem_persona_id=persona_id,
    )
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente, *, desde=date(2026, 1, 1), alta=None) -> Ingreso:
    n = _n()
    i = Ingreso(
        paciente_id=paciente.id, folio=f"F-CIT-{n}", folio_manual=True, fecha_ingreso=desde,
        fecha_alta=alta, tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="test citas", estado="activo",
    )
    db.add(i)
    db.flush()
    return i


def _persona(db, salutem_id: int, rut: str | None = RUT) -> SalutemPersona:
    p = SalutemPersona(
        salutem_id=salutem_id, rut=rut, contenido={}, hash_contenido="h",
        visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
    )
    db.add(p)
    db.flush()
    return p


def _cita(
    db, persona_id: int, fecha=FECHA, estado_id=1, *, especialidad="Medicina", profesional="Dr. X",
    desaparecida=None, cambiado_en=AHORA,
) -> SalutemCita:
    c = SalutemCita(
        cita_id=_n() + 900000, persona_id=persona_id, fecha_cita=fecha, estado_id=estado_id,
        contenido={"especialidadNombre": especialidad, "profesionalNombre": profesional},
        hash_contenido="h", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
        cambiado_en=cambiado_en, desaparecida_en=desaparecida,
    )
    db.add(c)
    db.flush()
    return c


def _filas(db) -> list[Cita]:
    return list(db.scalars(select(Cita).where(Cita.salutem_cita_id.is_not(None))).all())


def _escenario(db, **kw):
    paciente = _paciente(db)
    ingreso = _ingreso(db, paciente)
    _persona(db, 501)
    return paciente, ingreso, _cita(db, 501, **kw)


@pytest.mark.parametrize(
    ("estado_id", "esperado"),
    [
        (1, "agendada"), (4, "agendada"), (5, "agendada"), (6, "agendada"), (7, "agendada"),
        (8, "agendada"), (3, "realizada"), (9, "inasistencia"), (2, "anulada"),
        (99, None), (None, None),
    ],
)
def test_estado_cita_mapea_los_9_estados_y_desconocidos(estado_id, esperado):
    assert estado_cita(estado_id) == esperado


def test_importa_cita_cruzando_por_rut(db_session):
    _, ingreso, cita = _escenario(db_session, estado_id=3)

    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    (fila,) = _filas(db_session)
    assert r.creadas == 1
    assert (fila.ingreso_id, fila.estado, fila.fecha, fila.origen) == (
        ingreso.id, "realizada", FECHA, "SALUTEM",
    )
    assert fila.salutem_cita_id == cita.cita_id
    assert (fila.especialidad, fila.profesional_nombre) == ("Medicina", "Dr. X")
    assert db_session.scalars(
        select(AuditLog).where(AuditLog.actor == ACTOR, AuditLog.entity == "cita")
    ).first() is not None


def test_importa_cita_cruzando_por_persona_id(db_session):
    paciente = _paciente(db_session, rut=None, persona_id=777)
    ingreso = _ingreso(db_session, paciente)
    _persona(db_session, 777, rut=None)
    _cita(db_session, 777)

    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert r.creadas == 1
    assert _filas(db_session)[0].ingreso_id == ingreso.id


def test_ignora_personas_que_no_son_pacientes(db_session):
    _persona(db_session, 600, rut="999999999")
    _cita(db_session, 600)

    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert _filas(db_session) == []
    assert (r.creadas, r.actualizadas, r.eliminadas, r.sin_ingreso, r.ambiguas) == (0, 0, 0, 0, 0)


def test_cita_fuera_de_ventana_no_se_importa_y_cuenta_sin_ingreso(db_session):
    _paciente_ = _paciente(db_session)
    _ingreso(db_session, _paciente_, desde=date(2026, 6, 1))
    _persona(db_session, 501)
    _cita(db_session, 501, fecha=date(2026, 5, 10))

    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert _filas(db_session) == []
    assert r.sin_ingreso == 1
    assert r.eliminadas == 0


def test_dos_ingresos_gana_el_mas_reciente(db_session):
    paciente = _paciente(db_session)
    _ingreso(db_session, paciente, desde=date(2026, 1, 1))
    reciente = _ingreso(db_session, paciente, desde=date(2026, 4, 1))
    _persona(db_session, 501)
    _cita(db_session, 501, fecha=date(2026, 5, 10))

    sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert _filas(db_session)[0].ingreso_id == reciente.id


def test_cambio_de_estado_actualiza_la_fila(db_session):
    _, _, cita = _escenario(db_session, estado_id=1)
    sincronizar_citas(db_session, desde=None, ahora=AHORA)

    cita.estado_id = 9
    db_session.flush()
    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    (fila,) = _filas(db_session)
    assert fila.estado == "inasistencia"
    assert (r.creadas, r.actualizadas) == (0, 1)


def test_cita_desaparecida_borra_la_fila(db_session):
    _, _, cita = _escenario(db_session)
    sincronizar_citas(db_session, desde=None, ahora=AHORA)
    assert len(_filas(db_session)) == 1

    cita.desaparecida_en = AHORA
    db_session.flush()
    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert _filas(db_session) == []
    assert r.eliminadas == 1
    assert db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "cita", AuditLog.action == "DELETE")
    ).first() is not None


def test_reprogramada_fuera_de_ventana_borra_la_fila(db_session):
    paciente = _paciente(db_session)
    _ingreso(db_session, paciente, desde=date(2026, 1, 1), alta=date(2026, 6, 30))
    _persona(db_session, 501)
    cita = _cita(db_session, 501, fecha=date(2026, 5, 10))
    sincronizar_citas(db_session, desde=None, ahora=AHORA)
    assert len(_filas(db_session)) == 1

    cita.fecha_cita = date(2026, 8, 1)
    db_session.flush()
    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert _filas(db_session) == []
    assert r.eliminadas == 1


def test_ingreso_nuevo_trae_citas_pasadas_en_corrida_incremental(db_session):
    paciente = _paciente(db_session)
    _persona(db_session, 501)
    antiguo = AHORA - timedelta(days=10)
    _cita(db_session, 501, cambiado_en=antiguo)
    desde = AHORA - timedelta(hours=1)

    # Sin ingreso aun: nada que importar ni cambio reciente.
    assert sincronizar_citas(db_session, desde=desde, ahora=AHORA).creadas == 0

    ingreso = _ingreso(db_session, paciente)
    ingreso.updated_at = AHORA
    db_session.flush()
    r = sincronizar_citas(db_session, desde=desde, ahora=AHORA)

    assert r.creadas == 1
    assert len(_filas(db_session)) == 1


def test_persona_que_cruza_con_dos_pacientes_se_omite(db_session):
    # Uno cruza por RUT y el otro por salutem_persona_id: la misma persona, dos pacientes.
    _ingreso(db_session, _paciente(db_session))
    _ingreso(db_session, _paciente(db_session, rut="111111111", persona_id=501))
    _persona(db_session, 501)
    _cita(db_session, 501)

    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert _filas(db_session) == []
    assert r.ambiguas == 1
    assert r.creadas == 0


def test_anterior_a_citas_salutem_desde_no_se_importa(db_session):
    _escenario(db_session, fecha=date(2025, 12, 31))

    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert _filas(db_session) == []
    assert (r.creadas, r.sin_ingreso) == (0, 0)


def test_idempotente(db_session):
    _escenario(db_session)

    r1 = sincronizar_citas(db_session, desde=None, ahora=AHORA)
    r2 = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert len(_filas(db_session)) == 1
    assert r1.creadas == 1
    assert (r2.creadas, r2.actualizadas) == (0, 0)


def test_resuelve_profesional_por_nombre_con_espacios(db_session):
    prof = Profesional(nombre="Dra. Ana Rojas", origen="SIGE", activo=True)
    db_session.add(prof)
    db_session.flush()
    _escenario(db_session, profesional="  Dra. Ana Rojas ")

    sincronizar_citas(db_session, desde=None, ahora=AHORA)

    fila = _filas(db_session)[0]
    assert fila.profesional_id == prof.id
    assert fila.profesional_nombre == "Dra. Ana Rojas"


@pytest.mark.parametrize("nombre", ["", "   ", SIN_PROFESIONAL_SALUTEM])
def test_sin_profesional_queda_nulo(db_session, nombre):
    _escenario(db_session, profesional=nombre)

    sincronizar_citas(db_session, desde=None, ahora=AHORA)

    fila = _filas(db_session)[0]
    assert fila.profesional_nombre is None
    assert fila.profesional_id is None


def test_cuenta_agendadas_antiguas(db_session):
    paciente = _paciente(db_session)
    ingreso = _ingreso(db_session, paciente)
    hoy = AHORA.astimezone(timezone(timedelta(hours=-3))).date()
    for dias, origen in [(100, "SALUTEM"), (50, "SALUTEM"), (100, "SIGE")]:
        db_session.add(Cita(
            ingreso_id=ingreso.id, estado="agendada", fecha=hoy - timedelta(days=dias),
            origen=origen, salutem_cita_id=_n() + 5000 if origen == "SALUTEM" else None,
        ))
    db_session.flush()

    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert r.agendadas_antiguas == 1


def test_estado_desconocido_no_toca_la_fila(db_session):
    _, _, cita = _escenario(db_session, estado_id=1)
    sincronizar_citas(db_session, desde=None, ahora=AHORA)

    cita.estado_id = 99
    db_session.flush()
    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)

    (fila,) = _filas(db_session)
    assert fila.estado == "agendada"
    assert r.estado_desconocido == 1
    assert (r.creadas, r.actualizadas, r.eliminadas) == (0, 0, 0)
