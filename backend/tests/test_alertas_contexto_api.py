"""Contexto de una alerta (paciente, ingreso, cita) para gestionarla desde el panel."""

from datetime import date, datetime, timezone

from app.models.alertas import AlertaNotif
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemPersona

AHORA = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
PERSONA = 1180505


def _paciente_e_ingresos(db) -> tuple[Paciente, Ingreso]:
    p = Paciente(rut="390000065", nombre="Humberto Escobar", sexo="M", edad=50, region="Maule",
                 salutem_persona_id=PERSONA)
    db.add(p)
    db.flush()
    viejo = Ingreso(paciente_id=p.id, folio="F-2022-0001", folio_manual=True, fecha_ingreso=date(2022, 6, 1),
                    fecha_alta=date(2023, 1, 1), tipo_derivacion="DIEP", tipo_ingreso="convenio",
                    modelo_tratamiento="ambulatorio", diagnostico="prueba", estado="cerrado")
    actual = Ingreso(paciente_id=p.id, folio="F-2026-0063", folio_manual=True, fecha_ingreso=date(2026, 6, 1),
                     tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
                     diagnostico="prueba", estado="activo")
    db.add_all([viejo, actual])
    db.add(SalutemPersona(salutem_id=PERSONA, rut=None, contenido={}, hash_contenido="x",
                          visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA))
    db.flush()
    return p, actual


def _alerta(db, caso_tipo, caso_id, usuario_id=None) -> AlertaNotif:
    a = AlertaNotif(tipo="licencia_en_control", estado="pendiente", caso_id=caso_id, caso_tipo=caso_tipo,
                    usuario_id=usuario_id, plazo_objetivo=AHORA, ventana_dias=0, email_enviado=False)
    db.add(a)
    db.flush()
    return a


def test_contexto_de_una_alerta_de_control(as_admin, db_session):
    p, ingreso = _paciente_e_ingresos(db_session)
    c = ControlMedico(ingreso_id=ingreso.id, origen="SALUTEM", salutem_cita_id=16625887,
                      fecha_control=date(2026, 10, 15), semana_control=20, medico_tratante="DRA",
                      region_derivacion="Maule")
    db_session.add(c)
    db_session.flush()
    a = _alerta(db_session, "control_medico", c.id)

    r = as_admin.get(f"/api/v1/alertas/{a.id}/contexto")

    assert r.status_code == 200, r.text
    assert r.json() == {
        "paciente_id": p.id, "paciente_nombre": "Humberto Escobar", "ingreso_id": ingreso.id,
        "folio": "F-2026-0063", "cita_id": 16625887, "fecha": "2026-10-15",
    }


def test_contexto_de_una_atencion_toma_el_ingreso_de_su_fecha(as_admin, db_session):
    p, ingreso = _paciente_e_ingresos(db_session)
    db_session.add(SalutemAtencion(cita_id=16625886, persona_id=PERSONA, fecha_cita=date(2026, 10, 15),
                                   contenido={}, hash_contenido="x", visto_primera_vez=AHORA,
                                   visto_ultima_vez=AHORA, cambiado_en=AHORA))
    db_session.flush()
    a = _alerta(db_session, "salutem_atencion", 16625886)

    r = as_admin.get(f"/api/v1/alertas/{a.id}/contexto")

    assert r.json()["folio"] == "F-2026-0063"
    assert (r.json()["paciente_id"], r.json()["cita_id"]) == (p.id, 16625886)


def test_la_alerta_de_otra_administrativa_no_existe(as_admin, db_session):
    a = _alerta(db_session, "control_medico", 1, usuario_id=999999)
    assert as_admin.get(f"/api/v1/alertas/{a.id}/contexto").status_code == 404


def test_alerta_inexistente_da_404(as_admin):
    assert as_admin.get("/api/v1/alertas/999999/contexto").status_code == 404
