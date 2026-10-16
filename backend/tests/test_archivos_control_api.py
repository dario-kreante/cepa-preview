"""Documentos de la biblioteca de SALUTEM unidos a un control, y su descarga bajo demanda."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.integrations.salutem.errors import SalutemUnavailableError
from app.integrations.salutem.models import ContenidoArchivo
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion

AHORA = datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc)
PERSONA = 1180505


def _ingreso(db) -> Ingreso:
    p = Paciente(rut="390001180", nombre="Humberto Escobar", sexo="M", edad=50, region="Maule")
    db.add(p)
    db.flush()
    i = Ingreso(paciente_id=p.id, folio="F-2026-1180", folio_manual=True, fecha_ingreso=date(2026, 9, 1),
                tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
                diagnostico="prueba", estado="activo")
    db.add(i)
    db.flush()
    return i


def _control(db, ingreso, cita_id, fecha, persona=PERSONA) -> ControlMedico:
    db.add(SalutemAtencion(cita_id=cita_id, persona_id=persona, fecha_cita=fecha, contenido={},
                           hash_contenido="x", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
                           cambiado_en=AHORA))
    c = ControlMedico(ingreso_id=ingreso.id, origen="SALUTEM", salutem_cita_id=cita_id, fecha_control=fecha,
                      semana_control=7, medico_tratante="DRA", region_derivacion="Maule")
    db.add(c)
    db.flush()
    return c


def _archivo(db, archivo_id, creado, persona=PERSONA, desaparecido=None):
    db.add(SalutemArchivo(archivo_id=archivo_id, persona_id=persona, nombre=f"doc{archivo_id}.pdf",
                          tipo="documento", fecha_creacion=creado, visto_ultima_vez=AHORA,
                          desaparecido_en=desaparecido))
    db.flush()


@pytest.fixture
def escenario(db_session):
    ingreso = _ingreso(db_session)
    c1 = _control(db_session, ingreso, 16625887, date(2026, 10, 15))
    _control(db_session, ingreso, 16625990, date(2026, 10, 18))       # el control siguiente
    _archivo(db_session, 1, datetime(2026, 10, 15, 16, 29))            # mismo día → c1
    _archivo(db_session, 2, datetime(2026, 10, 17, 9, 0))              # antes del siguiente → c1
    _archivo(db_session, 3, datetime(2026, 10, 18, 9, 0))              # día del siguiente → no
    _archivo(db_session, 4, datetime(2026, 10, 14, 23, 59))            # día anterior → no
    _archivo(db_session, 5, datetime(2026, 10, 15, 17, 0), persona=999)  # otra persona → no
    _archivo(db_session, 6, datetime(2026, 10, 15, 18, 0), desaparecido=AHORA)  # borrado → no
    _archivo(db_session, 7, None)                                      # fecha ilegible → no
    return c1


def test_lista_los_archivos_del_dia_hasta_el_control_siguiente(as_admin, escenario):
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos")
    assert r.status_code == 200, r.text
    assert [a["archivo_id"] for a in r.json()] == [1, 2]
    assert r.json()[0] == {"archivo_id": 1, "nombre": "doc1.pdf", "tipo": "documento",
                           "fecha_creacion": "2026-10-15T16:29:00"}


def test_la_ventana_tiene_un_tope_de_siete_dias(as_admin, db_session):
    ingreso = _ingreso(db_session)
    c = _control(db_session, ingreso, 500, date(2026, 10, 1))
    _archivo(db_session, 10, datetime(2026, 10, 7, 23, 0))
    _archivo(db_session, 11, datetime(2026, 10, 8, 0, 1))
    r = as_admin.get(f"/api/v1/controles-medicos/{c.id}/archivos")
    assert [a["archivo_id"] for a in r.json()] == [10]


def test_un_control_sin_atencion_de_salutem_no_tiene_archivos(as_admin, db_session):
    ingreso = _ingreso(db_session)
    c = ControlMedico(ingreso_id=ingreso.id, origen="CEPA", fecha_control=date(2026, 10, 15),
                      semana_control=7, medico_tratante="DRA", region_derivacion="Maule")
    db_session.add(c)
    db_session.flush()
    assert as_admin.get(f"/api/v1/controles-medicos/{c.id}/archivos").json() == []


def test_el_contenido_se_pide_a_salutem_y_se_audita(as_admin, db_session, escenario, monkeypatch):
    pedidos = []

    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            pedidos.append((salutem_id, archivo_id))
            return ContenidoArchivo(nombre="LICENCIA 15 octubre.pdf", media_type="application/pdf", datos=b"%PDF-1.6")

    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client", lambda: Cliente())

    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/1/contenido")

    assert r.status_code == 200
    assert r.content == b"%PDF-1.6"
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith("inline;")
    # Defensa en profundidad: contenido clínico, sin caché y sin que el navegador adivine el tipo.
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert pedidos == [(PERSONA, 1)]
    auditoria = db_session.scalars(select(AuditLog).where(AuditLog.entity == "salutem_archivo")).all()
    assert [(a.action, a.entity_id) for a in auditoria] == [("READ", "1")]


@pytest.mark.parametrize("archivo_id", [3, 4, 5, 6, 999])
def test_un_archivo_que_no_es_del_control_no_se_descarga(as_admin, escenario, monkeypatch, archivo_id):
    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client",
                        lambda: pytest.fail("no debe llamar a SALUTEM"))
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/{archivo_id}/contenido")
    assert r.status_code == 404


def test_sin_contenido_en_salutem_responde_404(as_admin, escenario, monkeypatch):
    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            return None

    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client", lambda: Cliente())
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/1/contenido")
    assert r.status_code == 404
    assert r.json()["detail"] == "SALUTEM no entregó el contenido del archivo"


def test_salutem_caido_responde_502(as_admin, escenario, monkeypatch):
    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            raise SalutemUnavailableError("HTTP 504")

    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client", lambda: Cliente())
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/1/contenido")
    assert r.status_code == 502


def test_el_auditor_puede_leer(as_auditor, escenario):
    assert as_auditor.get(f"/api/v1/controles-medicos/{escenario.id}/archivos").status_code == 200


def test_sin_sesion_no_hay_acceso(client, escenario):
    assert client.get(f"/api/v1/controles-medicos/{escenario.id}/archivos").status_code == 401
