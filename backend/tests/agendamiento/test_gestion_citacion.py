"""Gestión de contacto con pacientes por citar: servicio y API."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.agendamiento import gestion
from app.agendamiento.enums import ResultadoGestion
from app.agendamiento.models import GestionCitacion
from app.models.audit_log import AuditLog
from app.models.paciente import Paciente
from app.models.profesional import Profesional

BASE = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
_seq = {"n": 0}


def _paciente(db) -> Paciente:
    _seq["n"] += 1
    p = Paciente(rut=None, nombre=f"Paciente Gestion {_seq['n']}", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    return p


def _profesional(db, nombre: str) -> Profesional:
    p = Profesional(nombre=nombre, origen="SIGE", activo=True)
    db.add(p)
    db.flush()
    return p


def _gestion(db, paciente, profesional, resultado, minutos: int = 0) -> GestionCitacion:
    g = GestionCitacion(
        paciente_id=paciente.id, profesional_id=profesional.id, resultado=resultado.value,
        nota=None, usuario="tester", created_at=BASE + timedelta(minutes=minutos),
    )
    db.add(g)
    db.flush()
    return g


def _url(paciente_id: int) -> str:
    return f"/api/v1/pacientes-por-citar/{paciente_id}/gestiones"


def test_registrar_gestion_201_y_auditoria(as_admin, db_session):
    pac, prof = _paciente(db_session), _profesional(db_session, "Dra Gestion A")
    r = as_admin.post(
        _url(pac.id),
        json={"profesional_id": prof.id, "resultado": "no_contesta", "nota": "  llamar   de nuevo "},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["resultado"] == "no_contesta"
    assert body["usuario"] == "admin_test"
    assert body["nota"] == "llamar de nuevo"
    auditoria = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "gestion_citacion", AuditLog.entity_id == str(body["id"])
        )
    ).all()
    assert len(auditoria) == 1


def test_registrar_gestion_auditor_403(as_auditor, db_session):
    pac, prof = _paciente(db_session), _profesional(db_session, "Dra Gestion B")
    r = as_auditor.post(_url(pac.id), json={"profesional_id": prof.id, "resultado": "otro"})
    assert r.status_code == 403


def test_registrar_gestion_resultado_invalido_422(as_admin, db_session):
    pac, prof = _paciente(db_session), _profesional(db_session, "Dra Gestion C")
    r = as_admin.post(_url(pac.id), json={"profesional_id": prof.id, "resultado": "inventado"})
    assert r.status_code == 422


def test_registrar_gestion_paciente_inexistente_404(as_admin, db_session):
    prof = _profesional(db_session, "Dra Gestion D")
    r = as_admin.post(_url(999_999_999), json={"profesional_id": prof.id, "resultado": "otro"})
    assert r.status_code == 404


def test_registrar_gestion_profesional_inexistente_404(as_admin, db_session):
    pac = _paciente(db_session)
    r = as_admin.post(_url(pac.id), json={"profesional_id": 999_999_999, "resultado": "otro"})
    assert r.status_code == 404


def test_listar_gestiones_orden_desc(as_auditor, db_session):
    pac, prof = _paciente(db_session), _profesional(db_session, "Dra Gestion E")
    vieja = _gestion(db_session, pac, prof, ResultadoGestion.NO_CONTESTA, 0)
    nueva = _gestion(db_session, pac, prof, ResultadoGestion.RECHAZA, 10)
    r = as_auditor.get(_url(pac.id))
    assert r.status_code == 200
    assert [g["id"] for g in r.json()] == [nueva.id, vieja.id]


def test_ultimas_gestiones_una_por_paciente(db_session):
    p1, p2, p3 = _paciente(db_session), _paciente(db_session), _paciente(db_session)
    a, b = _profesional(db_session, "Dra Gestion F"), _profesional(db_session, "Dr Gestion G")
    _gestion(db_session, p1, a, ResultadoGestion.NO_CONTESTA, 0)
    ultima_p1 = _gestion(db_session, p1, b, ResultadoGestion.RECHAZA, 5)
    # Empate en created_at para p2: gana el id más alto.
    _gestion(db_session, p2, a, ResultadoGestion.OTRO, 3)
    ultima_p2 = _gestion(db_session, p2, a, ResultadoGestion.NO_CONTESTA, 3)
    res = gestion.ultimas_gestiones(db_session, [p1.id, p2.id, p3.id])
    assert set(res) == {p1.id, p2.id}
    assert res[p1.id].id == ultima_p1.id
    assert res[p2.id].id == ultima_p2.id
    assert gestion.ultimas_gestiones(db_session, []) == {}


def test_ocultos_por_agendada_es_por_profesional(db_session):
    pac = _paciente(db_session)
    a, b = _profesional(db_session, "Dra Gestion H"), _profesional(db_session, "Dr Gestion I")
    _gestion(db_session, pac, a, ResultadoGestion.AGENDADA_EN_SALUTEM, 0)
    assert gestion.ocultos_por_agendada(db_session, a.id, [pac.id], BASE) == {pac.id}
    assert gestion.ocultos_por_agendada(db_session, b.id, [pac.id], BASE) == set()
    # Gestión anterior a `desde` no oculta.
    assert gestion.ocultos_por_agendada(db_session, a.id, [pac.id], BASE + timedelta(minutes=1)) == set()


def test_ultima_gestion_por_profesional(db_session):
    p1, p2 = _paciente(db_session), _paciente(db_session)
    a, b = _profesional(db_session, "Dra Gestion J"), _profesional(db_session, "Dr Gestion K")
    _gestion(db_session, p1, a, ResultadoGestion.AGENDADA_EN_SALUTEM, 0)
    esperada = _gestion(db_session, p1, a, ResultadoGestion.NO_CONTESTA, 7)  # cualquier resultado cuenta
    _gestion(db_session, p1, b, ResultadoGestion.AGENDADA_EN_SALUTEM, 30)  # otro profesional: no cuenta
    _gestion(db_session, p2, b, ResultadoGestion.AGENDADA_EN_SALUTEM, 1)
    res = gestion.ultima_gestion_por_profesional(db_session, a.id, [p1.id, p2.id])
    assert set(res) == {p1.id}
    assert res[p1.id].id == esperada.id
    assert gestion.ultima_gestion_por_profesional(db_session, a.id, []) == {}
