"""Alertas de licencia y receta emitidas en un control creado desde SALUTEM.

El fixture AHORA es 2026-09-16 (Santiago): las atenciones recientes van el 2026-09-10.
"""

from datetime import date, timezone

import pytest
from sqlalchemy import select

from app.config import get_settings

from app.integrations.salutem.models import AtencionSalutem, EstadoCitaSalutem, PersonaSalutem
from app.models.alertas import AlertaNotif
from app.models.config_alerta import ConfigAlerta
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.services.salutem_sync import copia
from app.services.salutem_sync.vinculacion import vincular
from tests.salutem_sync.conftest import AHORA

PERSONA = 1216099
ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
LICENCIA = {"antecedentes": [{"agrupacion": "", "nombre": "Indicación de reposo",
                              "registro": "Se extiende LM tipo 6 por 30 días"}]}
RECETA = {"indicaciones": [{"tipo": "Receta Medicamentos", "nombre": "Receta",
                            "registro": "Sertralina 50 mg (comprimido)\r\n 1 comprimido al día"}]}
CERTIFICADO = {"indicaciones": [{"tipo": "Documento", "nombre": "Documentos",
                                 "registro": "quien debe permanecer en reposo desde el 10-09-2026"}]}


def _ingreso(db) -> Ingreso:
    paciente = Paciente(rut="390000099", nombre="Paciente Alerta", sexo="F", edad=40,
                        region="Maule", salutem_persona_id=PERSONA)
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(paciente_id=paciente.id, folio="F-2026-0099", folio_manual=True,
                      fecha_ingreso=date(2026, 8, 1), tipo_derivacion="DIEP", tipo_ingreso="convenio",
                      modelo_tratamiento="ambulatorio", diagnostico="prueba", estado="activo")
    db.add(ingreso)
    db.flush()
    copia.guardar_persona(db, PersonaSalutem.desde_api({"SALUTEM_ID": PERSONA, "identificacion": "390000099"}), AHORA)
    return ingreso


def _atencion(db, cita_id, fecha="2026-09-10", estado=ATENDIDO, **contenido):
    copia.guardar_atencion(db, AtencionSalutem.desde_api({
        "personaId": PERSONA, "citaId": cita_id, "citaFecha": fecha, "estadoCitaId": estado,
        "estadoCitaNombre": "Atendido", "especialidadNombre": "Médico/a",
        "profesionalNombre": "DRA. PAULA ROJAS", **contenido,
    }), AHORA)


def _alertas(db) -> list[AlertaNotif]:
    return list(db.scalars(select(AlertaNotif).order_by(AlertaNotif.tipo)))


def test_control_nuevo_con_licencia_y_receta_crea_una_alerta_de_cada_tipo(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7001, **LICENCIA, **RECETA)

    vincular(db_session, AHORA)

    [control] = db_session.scalars(select(ControlMedico)).all()
    alertas = _alertas(db_session)
    assert [a.tipo for a in alertas] == ["licencia_en_control", "receta_en_control"]
    for a in alertas:
        assert (a.caso_tipo, a.caso_id, a.estado, a.ventana_dias) == ("control_medico", control.id, "pendiente", 0)
        assert a.plazo_objetivo.astimezone(timezone.utc).date() == date(2026, 9, 10)


def test_el_certificado_de_reposo_alerta_licencia(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7002, **CERTIFICADO)

    vincular(db_session, AHORA)

    assert [a.tipo for a in _alertas(db_session)] == ["licencia_en_control"]


def test_control_sin_licencia_ni_receta_no_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7003)

    vincular(db_session, AHORA)

    assert _alertas(db_session) == []


def test_al_cambiar_la_atencion_no_se_duplica_la_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7004, **LICENCIA)
    vincular(db_session, AHORA)
    _atencion(db_session, 7004, **LICENCIA, evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)

    assert len(_alertas(db_session)) == 1


def test_una_alerta_resuelta_no_reaparece(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7005, **LICENCIA)
    vincular(db_session, AHORA)
    [a] = _alertas(db_session)
    a.estado = "resuelta"
    db_session.flush()
    _atencion(db_session, 7005, **LICENCIA, evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)

    assert [x.estado for x in _alertas(db_session)] == ["resuelta"]


def test_un_control_antiguo_no_alerta(db_session):
    """Una re-vinculación completa no debe inundar de alertas por controles viejos."""
    _ingreso(db_session)
    _atencion(db_session, 7006, fecha="2026-08-20", **LICENCIA)  # 27 días antes de AHORA

    vincular(db_session, AHORA, todo=True)

    assert db_session.scalars(select(ControlMedico)).first() is not None
    assert _alertas(db_session) == []


def test_tipo_apagado_en_la_configuracion_no_alerta(db_session):
    _ingreso(db_session)
    db_session.add(ConfigAlerta(tipo="receta_en_control", dias=0, habiles=False, activo=False))
    db_session.flush()
    _atencion(db_session, 7007, **LICENCIA, **RECETA)

    vincular(db_session, AHORA)

    assert [a.tipo for a in _alertas(db_session)] == ["licencia_en_control"]


def test_al_anularse_la_atencion_sus_alertas_quedan_resueltas(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7008, **LICENCIA)
    vincular(db_session, AHORA)
    _atencion(db_session, 7008, estado=int(EstadoCitaSalutem.ANULADO), **LICENCIA)

    vincular(db_session, AHORA)

    [a] = _alertas(db_session)
    assert a.estado == "resuelta"
    assert a.resuelta_en is not None


def test_revincular_todo_sin_cambios_no_genera_alertas(db_session):
    """Desplegar y correr `fria` no debe alertar controles recientes que ya existían."""
    _ingreso(db_session)
    _atencion(db_session, 7007, **LICENCIA, **RECETA)
    vincular(db_session, AHORA)
    for a in _alertas(db_session):  # simula el estado previo al despliegue de la función
        db_session.delete(a)
    db_session.flush()

    vincular(db_session, AHORA, todo=True)

    assert _alertas(db_session) == []


def test_si_la_atencion_cambia_un_control_existente_sin_alerta_si_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7008, **LICENCIA)
    vincular(db_session, AHORA)
    for a in _alertas(db_session):
        db_session.delete(a)
    db_session.flush()
    _atencion(db_session, 7008, **LICENCIA, evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA, todo=True)

    assert [a.tipo for a in _alertas(db_session)] == ["licencia_en_control"]


def test_el_actor_de_la_alerta_es_el_mismo_del_resto_del_sync(db_session):
    from app.models.audit_log import AuditLog  # noqa: PLC0415

    _ingreso(db_session)
    _atencion(db_session, 7009, **LICENCIA)

    vincular(db_session, AHORA)

    actores = set(db_session.scalars(select(AuditLog.actor).where(AuditLog.entity == "alerta_notif")))
    assert actores == {"sistema:salutem-sync"}


def test_un_control_que_gana_licencia_en_la_revinculacion_alerta(db_session):
    """Caso real de QA (15-10-2026): el control quedó sin licencia porque el extractor no
    reconocía "Reposo por 15 días"; al reconocerla, la re-vinculación completa alerta."""
    _ingreso(db_session)
    _atencion(db_session, 7010, antecedentes=[
        {"nombre": "Indicación de reposo", "registro": "Reposo por 15 días desde el 10/09/2026"}])
    vincular(db_session, AHORA)
    [control] = db_session.scalars(select(ControlMedico)).all()
    # Como lo dejó el extractor anterior: sin licencia y sin alerta.
    control.tiene_licencia = False
    for a in _alertas(db_session):
        db_session.delete(a)
    db_session.flush()

    vincular(db_session, AHORA, todo=True)  # la atención no cambió en SALUTEM

    assert control.tiene_licencia is True
    assert [a.tipo for a in _alertas(db_session)] == ["licencia_en_control"]


def test_la_revinculacion_sin_cambios_no_repite_alertas(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7011, **LICENCIA)
    vincular(db_session, AHORA)
    [a] = _alertas(db_session)
    a.estado = "resuelta"
    db_session.flush()

    vincular(db_session, AHORA, todo=True)

    assert [x.estado for x in _alertas(db_session)] == ["resuelta"]


# ── Atenciones médicas que no son control (Evaluación médica, psiquiátrica) ──────
# Desde QA-002 (22-10-2026) las evaluaciones médicas son control por defecto; estas pruebas
# cubren la vía de SALUTEM_ESPECIALIDADES_ALERTA con un .env que deja solo Médico/a.

EVALUACION = {"especialidadNombre": "Evaluación médica"}
REPOSO = {"antecedentes": [{"nombre": "Indicación de reposo",
                            "registro": "Reposo por 15 días desde el 10/09/2026"}]}


@pytest.fixture
def control_solo_medico(monkeypatch):
    monkeypatch.setattr(get_settings(), "salutem_especialidades_control", "Médico/a")


def test_evaluacion_medica_con_licencia_alerta_aunque_no_sea_control(db_session, control_solo_medico):
    """Caso real de QA (15-10-2026): la licencia se emitió en una Evaluación médica."""
    _ingreso(db_session)
    _atencion(db_session, 7020, **EVALUACION, **REPOSO)

    vincular(db_session, AHORA)

    assert db_session.scalars(select(ControlMedico)).all() == []
    [a] = _alertas(db_session)
    assert (a.tipo, a.caso_tipo, a.caso_id, a.estado) == ("licencia_en_control", "salutem_atencion", 7020, "pendiente")
    assert a.plazo_objetivo.astimezone(timezone.utc).date() == date(2026, 9, 10)


def test_evaluacion_psiquiatrica_con_receta_alerta(db_session, control_solo_medico):
    _ingreso(db_session)
    _atencion(db_session, 7021, especialidadNombre="Evaluación psiquiátrica", **RECETA)

    vincular(db_session, AHORA)

    assert [(a.tipo, a.caso_tipo) for a in _alertas(db_session)] == [("receta_en_control", "salutem_atencion")]


def test_la_atencion_no_medica_no_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7022, especialidadNombre="Psicología", **REPOSO, **RECETA)

    vincular(db_session, AHORA)

    assert _alertas(db_session) == []


def test_la_alerta_de_la_atencion_no_se_repite_ni_reaparece(db_session, control_solo_medico):
    _ingreso(db_session)
    _atencion(db_session, 7023, **EVALUACION, **REPOSO)
    vincular(db_session, AHORA)
    [a] = _alertas(db_session)
    a.estado = "resuelta"
    db_session.flush()
    _atencion(db_session, 7023, **EVALUACION, **REPOSO, evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)
    vincular(db_session, AHORA, todo=True)

    assert [x.estado for x in _alertas(db_session)] == ["resuelta"]


def test_al_anularse_la_evaluacion_su_alerta_queda_resuelta(db_session, control_solo_medico):
    _ingreso(db_session)
    _atencion(db_session, 7024, **EVALUACION, **REPOSO)
    vincular(db_session, AHORA)
    _atencion(db_session, 7024, estado=int(EstadoCitaSalutem.ANULADO), **EVALUACION, **REPOSO)

    vincular(db_session, AHORA)

    [a] = _alertas(db_session)
    assert a.estado == "resuelta"


def test_una_evaluacion_antigua_no_alerta(db_session, control_solo_medico):
    _ingreso(db_session)
    _atencion(db_session, 7025, fecha="2026-08-20", **EVALUACION, **REPOSO)

    vincular(db_session, AHORA, todo=True)

    assert _alertas(db_session) == []


# ── La evaluación médica es control por defecto (QA-002, 22-10-2026) ─────────────


def test_la_evaluacion_medica_es_control_y_su_licencia_alerta_al_control(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7030, **EVALUACION, **REPOSO)

    vincular(db_session, AHORA)

    [c] = db_session.scalars(select(ControlMedico)).all()
    [a] = _alertas(db_session)
    assert (a.tipo, a.caso_tipo, a.caso_id) == ("licencia_en_control", "control_medico", c.id)


def test_la_atencion_que_pasa_a_control_no_duplica_su_alerta(db_session, monkeypatch):
    """La evaluación alertó como atención; al ampliarse las especialidades de control
    (y re-vincular todo) se crea el control, pero la alerta no se repite y la de la
    atención sigue abierta."""
    monkeypatch.setattr(get_settings(), "salutem_especialidades_control", "Médico/a")
    _ingreso(db_session)
    _atencion(db_session, 7031, **EVALUACION, **REPOSO, **RECETA)
    vincular(db_session, AHORA)
    assert [(a.caso_tipo, a.estado) for a in _alertas(db_session)] == [
        ("salutem_atencion", "pendiente"), ("salutem_atencion", "pendiente"),
    ]
    monkeypatch.undo()
    # Un cambio en SALUTEM también fuerza la alerta del control: tampoco debe duplicar.
    _atencion(db_session, 7031, **EVALUACION, **REPOSO, **RECETA,
              evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)
    vincular(db_session, AHORA, todo=True)

    assert len(db_session.scalars(select(ControlMedico)).all()) == 1
    assert [(a.caso_tipo, a.caso_id, a.estado) for a in _alertas(db_session)] == [
        ("salutem_atencion", 7031, "pendiente"), ("salutem_atencion", 7031, "pendiente"),
    ]


def test_la_alerta_resuelta_de_la_atencion_no_reaparece_en_el_control(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "salutem_especialidades_control", "Médico/a")
    _ingreso(db_session)
    _atencion(db_session, 7032, **EVALUACION, **REPOSO)
    vincular(db_session, AHORA)
    [a] = _alertas(db_session)
    a.estado = "resuelta"
    db_session.flush()
    monkeypatch.undo()

    vincular(db_session, AHORA, todo=True)

    assert len(db_session.scalars(select(ControlMedico)).all()) == 1
    assert [(x.caso_tipo, x.estado) for x in _alertas(db_session)] == [("salutem_atencion", "resuelta")]
