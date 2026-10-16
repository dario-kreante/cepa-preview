"""Completar el registro de un paciente borrador = crearle su ingreso con folio."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.domain.enums import EstadoRegistroPaciente as Estado
from app.models.alertas import AlertaNotif
from app.models.audit_log import AuditLog
from app.models.ficha_clinica import FichaClinica
from app.models.paciente import Paciente
from app.services.salutem_sync.vinculacion import vincular
from tests.salutem_sync.conftest import AHORA
from tests.salutem_sync.test_borradores import _atendida


def _payload(**over):
    base = {
        "nombre": "Ana Prueba",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "Trastorno adaptativo",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-09-01",
    }
    base.update(over)
    return base


def _borrador(db, rut="123456785", estado=Estado.PENDIENTE_FOLIO.value, persona_id=None, **extra):
    p = Paciente(nombre="ANA PRUEBA", rut=rut, estado_registro=estado, origen="SALUTEM",
                 salutem_persona_id=persona_id, **extra)
    db.add(p)
    db.flush()
    if estado == Estado.PENDIENTE_FOLIO.value:
        db.add(AlertaNotif(
            tipo="paciente_pendiente_folio", estado="pendiente", caso_id=p.id, caso_tipo="paciente",
            usuario_id=None, plazo_objetivo=datetime.now(timezone.utc), ventana_dias=0,
            email_enviado=False,
        ))
    db.commit()
    return p


def _alerta(db, paciente_id):
    return db.scalars(select(AlertaNotif).where(AlertaNotif.caso_id == paciente_id)).one()


def test_completar_con_folio_manual(as_admin, db_session):
    p = _borrador(db_session)
    r = as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id, folio="CEPA-0099", nombre="Ana Completa"))
    assert r.status_code == 201, r.text
    assert r.json()["folio"] == "CEPA-0099"
    db_session.expire_all()
    p = db_session.get(Paciente, p.id)
    assert p.estado_registro == Estado.COMPLETO.value
    assert p.nombre == "Ana Completa" and p.edad == 33 and p.region == "Maule"
    assert _alerta(db_session, p.id).estado == "resuelta"
    auditoria = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "paciente", AuditLog.entity_id == str(p.id))
    ).all()
    assert [a.action for a in auditoria] == ["UPDATE"]


def test_completar_con_folio_automatico(as_admin, db_session):
    p = _borrador(db_session)
    r = as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id))
    assert r.status_code == 201, r.text
    assert r.json()["folio"].startswith("F-")


def test_borrador_sin_rut_se_completa_sin_rut(as_admin, db_session):
    p = _borrador(db_session, rut=None)
    r = as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id))
    assert r.status_code == 201, r.text
    db_session.expire_all()
    p = db_session.get(Paciente, p.id)
    assert p.rut is None and p.estado_registro == Estado.COMPLETO.value


def test_borrador_sin_rut_acepta_un_rut_nuevo(as_admin, db_session):
    p = _borrador(db_session, rut=None)
    r = as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id, rut="12.345.678-5"))
    assert r.status_code == 201, r.text
    db_session.expire_all()
    assert db_session.get(Paciente, p.id).rut == "123456785"


def test_borrador_con_rut_lo_conserva_si_no_llega(as_admin, db_session):
    p = _borrador(db_session, rut="123456785")
    assert as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id)).status_code == 201
    db_session.expire_all()
    assert db_session.get(Paciente, p.id).rut == "123456785"


def test_sin_paciente_id_y_sin_rut_es_422(as_admin):
    assert as_admin.post("/api/v1/ingresos", json=_payload()).status_code == 422


def test_rut_de_otro_paciente_es_409_y_el_borrador_sigue_pendiente(as_admin, db_session):
    _borrador(db_session, rut="123456785", estado=Estado.COMPLETO.value)
    p = _borrador(db_session, rut=None)
    r = as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id, rut="12.345.678-5"))
    assert r.status_code == 409
    assert "ya pertenece a otro paciente" in r.json()["detail"]
    db_session.expire_all()
    assert db_session.get(Paciente, p.id).estado_registro == Estado.PENDIENTE_FOLIO.value
    assert _alerta(db_session, p.id).estado != "resuelta"


def test_paciente_inexistente_es_404(as_admin):
    assert as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=999999)).status_code == 404


def test_paciente_completo_o_descartado_con_paciente_id_es_409(as_admin, db_session):
    c = _borrador(db_session, rut="111111111", estado=Estado.COMPLETO.value)
    d = _borrador(db_session, rut="222222222", estado=Estado.DESCARTADO.value)
    for p in (c, d):
        assert as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id)).status_code == 409


def test_ingreso_por_rut_de_un_borrador_lo_deja_completo(as_admin, db_session):
    p = _borrador(db_session)
    r = as_admin.post("/api/v1/ingresos", json=_payload(rut="12.345.678-5"))
    assert r.status_code == 201, r.text
    db_session.expire_all()
    assert db_session.get(Paciente, p.id).estado_registro == Estado.COMPLETO.value
    assert _alerta(db_session, p.id).estado == "resuelta"


def test_ingreso_por_rut_de_un_descartado_lo_deja_completo_y_limpia_el_descarte(as_admin, db_session):
    p = _borrador(
        db_session, estado=Estado.DESCARTADO.value, motivo_descarte="duplicado",
        descartado_por="admin_test", descartado_en=datetime.now(timezone.utc),
    )
    assert as_admin.post("/api/v1/ingresos", json=_payload(rut="12.345.678-5")).status_code == 201
    db_session.expire_all()
    p = db_session.get(Paciente, p.id)
    assert p.estado_registro == Estado.COMPLETO.value
    assert p.motivo_descarte is None and p.descartado_por is None and p.descartado_en is None


def test_vincular_tras_completar_une_las_fichas_de_salutem(as_admin, db_session):
    _atendida(db_session, salutem_id=7100, identificacion="12345678-5")
    p = _borrador(db_session, persona_id=7100)
    vincular(db_session, AHORA)
    antes = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert db_session.scalars(select(FichaClinica)).all() == []

    assert as_admin.post("/api/v1/ingresos", json=_payload(paciente_id=p.id, fecha_ingreso="2026-09-01")).status_code == 201
    r = vincular(db_session, AHORA, ingresos_desde=antes)

    assert r.fichas_nuevas == 1
    assert len(db_session.scalars(select(FichaClinica)).all()) == 1
