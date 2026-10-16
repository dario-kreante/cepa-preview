"""API de pacientes borrador: lista de pendientes de folio, descarte y buscador."""

from datetime import date, datetime, timezone

from sqlalchemy import select

from app.models.alertas import AlertaNotif
from app.models.audit_log import AuditLog
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemPersona

_T = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)


def _persona(db, salutem_id, identificacion, rut=None):
    db.add(SalutemPersona(salutem_id=salutem_id, rut=rut, contenido={"identificacion": identificacion},
                          hash_contenido="h", visto_primera_vez=_T, visto_ultima_vez=_T, cambiado_en=_T))


def _atencion(db, cita_id, persona_id, fecha, especialidad):
    db.add(SalutemAtencion(cita_id=cita_id, persona_id=persona_id, fecha_cita=fecha,
                           contenido={"especialidadNombre": especialidad}, hash_contenido="h",
                           visto_primera_vez=_T, visto_ultima_vez=_T, cambiado_en=_T))


def _borrador(db, nombre="Ana Borrador", persona_id=None, estado="pendiente_folio", rut=None):
    p = Paciente(nombre=nombre, rut=rut, estado_registro=estado, origen="SALUTEM",
                 salutem_persona_id=persona_id)
    db.add(p)
    db.flush()
    return p


def _alerta(db, paciente_id):
    a = AlertaNotif(tipo="paciente_pendiente_folio", estado="pendiente", caso_id=paciente_id,
                    caso_tipo="paciente", usuario_id=None, plazo_objetivo=_T, ventana_dias=0,
                    email_enviado=False)
    db.add(a)
    db.flush()
    return a


def test_lista_resume_las_atenciones_del_borrador(as_admin, db_session):
    _persona(db_session, 9001, "sin_id_1141409")
    p = _borrador(db_session, persona_id=9001)
    _atencion(db_session, 1, 9001, date(2026, 9, 10), "Médico/a")
    _atencion(db_session, 2, 9001, date(2026, 9, 14), "Psicólogo/a")
    _atencion(db_session, 3, 9001, date(2026, 9, 15), "Médico/a")

    r = as_admin.get("/api/v1/pacientes/pendientes-folio")

    assert r.status_code == 200
    [fila] = r.json()
    assert fila["id"] == p.id
    assert fila["nombre"] == "Ana Borrador"
    assert fila["rut"] is None
    assert fila["identificacion_salutem"] == "sin_id_1141409"
    assert fila["salutem_persona_id"] == 9001
    assert fila["primera_atencion"] == "2026-09-10"
    assert fila["ultima_atencion"] == "2026-09-15"
    assert fila["atenciones"] == 3
    assert sorted(fila["especialidades"]) == ["Médico/a", "Psicólogo/a"]
    assert "creado_en" in fila


def test_lista_excluye_completos_y_descartados(as_admin, db_session):
    _borrador(db_session, "Pendiente")
    _borrador(db_session, "Descartado", estado="descartado")
    _borrador(db_session, "Completo", estado="completo")

    r = as_admin.get("/api/v1/pacientes/pendientes-folio")

    assert [f["nombre"] for f in r.json()] == ["Pendiente"]
    assert r.json()[0]["atenciones"] == 0
    assert r.json()[0]["primera_atencion"] is None


def test_lista_solo_administrativo_y_coordinacion(as_auditor, as_admin, as_coordinacion):
    assert as_auditor.get("/api/v1/pacientes/pendientes-folio").status_code == 403
    assert as_admin.get("/api/v1/pacientes/pendientes-folio").status_code == 200
    assert as_coordinacion.get("/api/v1/pacientes/pendientes-folio").status_code == 200


def test_descartar_sin_motivo_es_422(as_admin, db_session):
    p = _borrador(db_session)
    assert as_admin.post(f"/api/v1/pacientes/{p.id}/descartar", json={}).status_code == 422
    assert as_admin.post(f"/api/v1/pacientes/{p.id}/descartar", json={"motivo": ""}).status_code == 422


def test_descartar_registra_motivo_actor_alerta_y_auditoria(as_admin, db_session):
    p = _borrador(db_session)
    alerta = _alerta(db_session, p.id)

    r = as_admin.post(f"/api/v1/pacientes/{p.id}/descartar", json={"motivo": "Paciente de prueba"})

    assert r.status_code == 200
    assert r.json()["estado_registro"] == "descartado"
    db_session.refresh(p)
    db_session.refresh(alerta)
    assert (p.motivo_descarte, p.descartado_por) == ("Paciente de prueba", "admin_test")
    assert p.descartado_en is not None
    assert alerta.estado == "resuelta"
    acciones = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "paciente", AuditLog.entity_id == str(p.id))
    ).all()
    assert [(a.actor, a.action) for a in acciones] == [("admin_test", "UPDATE")]


def test_descartar_un_completo_es_409(as_admin, db_session):
    p = _borrador(db_session, estado="completo")
    r = as_admin.post(f"/api/v1/pacientes/{p.id}/descartar", json={"motivo": "x"})
    assert r.status_code == 409


def test_descartar_inexistente_es_404(as_admin):
    assert as_admin.post("/api/v1/pacientes/999999/descartar", json={"motivo": "x"}).status_code == 404


def test_descartar_auditor_es_403(as_auditor, db_session):
    p = _borrador(db_session)
    assert as_auditor.post(f"/api/v1/pacientes/{p.id}/descartar", json={"motivo": "x"}).status_code == 403


def test_buscador_incluye_borrador_y_excluye_descartado(as_auditor, db_session):
    _borrador(db_session, "Zoe Buscable")
    _borrador(db_session, "Zoe Descartada", estado="descartado")

    r = as_auditor.get("/api/v1/pacientes/buscar", params={"q": "Zoe"})

    assert r.status_code == 200
    assert [(x["nombre"], x["estado_registro"]) for x in r.json()] == [("Zoe Buscable", "pendiente_folio")]
