"""Biblioteca de SALUTEM del paciente con la relación deducida con licencia o receta (QA-001)."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.integrations.salutem.errors import SalutemUnavailableError
from app.integrations.salutem.models import ContenidoArchivo
from app.models.audit_log import AuditLog
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion, SalutemPersona

AHORA = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)
PERSONA = 1180505
OTRA_PERSONA_DEL_PACIENTE = 777  # sin fila en salutem_persona: llega por un control

CERTIFICADO = {"indicaciones": [{"tipo": "Documento", "nombre": "Documentos",
                                 "registro": "quien debe permanecer en reposo desde el 01-10-2026"}]}
RECETA = {"indicaciones": [{"tipo": "Receta Medicamentos", "nombre": "Receta",
                            "registro": "Sertralina 50 mg (comprimido) 1 al día"}]}
AMBAS = {"indicaciones": CERTIFICADO["indicaciones"] + RECETA["indicaciones"]}


def _paciente(db) -> tuple[Paciente, Ingreso]:
    p = Paciente(rut="390001180", nombre="Humberto Escobar", sexo="M", edad=50, region="Maule")
    db.add(p)
    db.flush()
    i = Ingreso(paciente_id=p.id, folio="F-2026-1180", folio_manual=True, fecha_ingreso=date(2026, 9, 1),
                tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
                diagnostico="prueba", estado="activo")
    db.add(i)
    db.add(SalutemPersona(salutem_id=PERSONA, rut="390001180", contenido={}, hash_contenido="x",
                          visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA))
    db.flush()
    return p, i


def _atencion(db, cita_id, fecha, contenido, persona=PERSONA):
    db.add(SalutemAtencion(cita_id=cita_id, persona_id=persona, fecha_cita=fecha, contenido=contenido,
                           hash_contenido="x", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
                           cambiado_en=AHORA))
    db.flush()


def _control(db, ingreso, cita_id, fecha, tiene_licencia=False):
    db.add(ControlMedico(ingreso_id=ingreso.id, origen="SALUTEM", salutem_cita_id=cita_id, fecha_control=fecha,
                         semana_control=7, medico_tratante="DRA", region_derivacion="Maule",
                         tiene_licencia=tiene_licencia))
    db.flush()


def _archivo(db, archivo_id, creado, persona=PERSONA, desaparecido=None, tipo="documento"):
    db.add(SalutemArchivo(archivo_id=archivo_id, persona_id=persona, nombre=f"doc{archivo_id}.pdf",
                          tipo=tipo, fecha_creacion=creado, visto_ultima_vez=AHORA,
                          desaparecido_en=desaparecido))
    db.flush()


@pytest.fixture
def paciente(db_session) -> Paciente:
    db = db_session
    p, ingreso = _paciente(db)
    _atencion(db, 101, date(2026, 10, 1), CERTIFICADO)            # licencia
    _atencion(db, 110, date(2026, 10, 10), RECETA)                # receta
    _atencion(db, 112, date(2026, 10, 12), {})                    # control con licencia en SIGE
    _control(db, ingreso, 112, date(2026, 10, 12), tiene_licencia=True)
    _atencion(db, 120, date(2026, 10, 20), {})                    # sin licencia ni receta
    _atencion(db, 125, date(2026, 10, 25), AMBAS)                 # licencia y receta
    _atencion(db, 777, date(2026, 10, 15), {}, persona=OTRA_PERSONA_DEL_PACIENTE)
    _control(db, ingreso, 777, date(2026, 10, 15))

    _archivo(db, 1, datetime(2026, 10, 1, 10, 0))                 # mismo día → licencia
    _archivo(db, 2, datetime(2026, 10, 5, 9, 0))                  # dentro de 7 días → licencia
    _archivo(db, 3, datetime(2026, 10, 8, 9, 0))                  # día 7 → sin relación
    _archivo(db, 4, datetime(2026, 10, 11, 9, 0), tipo="imagen")  # tras la receta → receta
    _archivo(db, 5, datetime(2026, 10, 13, 9, 0))                 # la última atención manda → licencia
    _archivo(db, 6, datetime(2026, 10, 21, 9, 0))                 # la del 20 no indicó nada → sin relación
    _archivo(db, 11, datetime(2026, 10, 25, 18, 0))               # licencia y receta
    _archivo(db, 10, datetime(2026, 10, 15, 12, 0), persona=OTRA_PERSONA_DEL_PACIENTE)
    _archivo(db, 7, datetime(2026, 10, 1, 11, 0), persona=999)    # otra persona → no
    _archivo(db, 8, datetime(2026, 10, 1, 12, 0), desaparecido=AHORA)  # borrado → no
    _archivo(db, 9, None)                                          # fecha ilegible → al final
    return p


def _url(p, sufijo=""):
    return f"/api/v1/pacientes/{p.id}/documentos-salutem{sufijo}"


def test_lista_toda_la_biblioteca_del_paciente_del_mas_nuevo_al_mas_antiguo(as_admin, paciente):
    r = as_admin.get(_url(paciente))
    assert r.status_code == 200, r.text
    assert [d["archivo_id"] for d in r.json()] == [11, 6, 10, 5, 4, 3, 2, 1, 9]
    assert r.json()[0] == {"archivo_id": 11, "nombre": "doc11.pdf", "tipo": "documento",
                           "fecha_creacion": "2026-10-25T18:00:00", "licencia": True, "receta": True,
                           "fecha_atencion": "2026-10-25"}
    sin_relacion = {d["archivo_id"] for d in r.json() if not d["licencia"] and not d["receta"]}
    assert sin_relacion == {6, 10, 3, 9}


def test_filtra_los_relacionados_con_licencia(as_admin, paciente):
    r = as_admin.get(_url(paciente, "?relacion=licencia"))
    assert [d["archivo_id"] for d in r.json()] == [11, 5, 2, 1]
    assert {d["archivo_id"]: d["fecha_atencion"] for d in r.json()}[5] == "2026-10-12"


def test_filtra_los_relacionados_con_receta(as_admin, paciente):
    r = as_admin.get(_url(paciente, "?relacion=receta"))
    assert [(d["archivo_id"], d["tipo"]) for d in r.json()] == [(11, "documento"), (4, "imagen")]


def test_una_relacion_desconocida_es_422(as_admin, paciente):
    assert as_admin.get(_url(paciente, "?relacion=oda")).status_code == 422


def test_paciente_sin_salutem_no_tiene_documentos(as_admin, db_session):
    p = Paciente(rut="111111111", nombre="Sin Salutem", sexo="F", edad=30, region="Maule")
    db_session.add(p)
    db_session.flush()
    assert as_admin.get(_url(p)).json() == []


def test_paciente_inexistente_es_404(as_admin):
    assert as_admin.get("/api/v1/pacientes/999999/documentos-salutem").status_code == 404


def test_el_contenido_se_pide_a_salutem_con_la_persona_del_archivo(as_admin, db_session, paciente, monkeypatch):
    pedidos = []

    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            pedidos.append((salutem_id, archivo_id))
            return ContenidoArchivo(nombre="RECETA.pdf", media_type="application/pdf", datos=b"%PDF-1.6")

    monkeypatch.setattr("app.routers.documentos_salutem.get_salutem_client", lambda: Cliente())

    r = as_admin.get(_url(paciente, "/4/contenido"))
    assert r.status_code == 200
    assert r.content == b"%PDF-1.6"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert as_admin.get(_url(paciente, "/10/contenido")).status_code == 200
    assert pedidos == [(PERSONA, 4), (OTRA_PERSONA_DEL_PACIENTE, 10)]
    auditoria = db_session.scalars(select(AuditLog).where(AuditLog.entity == "salutem_archivo")).all()
    assert [(a.action, a.entity_id) for a in auditoria] == [("READ", "4"), ("READ", "10")]


@pytest.mark.parametrize("archivo_id", [7, 8, 12345])
def test_un_archivo_que_no_es_del_paciente_no_se_descarga(as_admin, paciente, monkeypatch, archivo_id):
    monkeypatch.setattr("app.routers.documentos_salutem.get_salutem_client",
                        lambda: pytest.fail("no debe llamar a SALUTEM"))
    assert as_admin.get(_url(paciente, f"/{archivo_id}/contenido")).status_code == 404


def test_salutem_caido_responde_502(as_admin, paciente, monkeypatch):
    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            raise SalutemUnavailableError("HTTP 504")

    monkeypatch.setattr("app.routers.documentos_salutem.get_salutem_client", lambda: Cliente())
    assert as_admin.get(_url(paciente, "/1/contenido")).status_code == 502


def test_sin_contenido_en_salutem_responde_404(as_admin, paciente, monkeypatch):
    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            return None

    monkeypatch.setattr("app.routers.documentos_salutem.get_salutem_client", lambda: Cliente())
    r = as_admin.get(_url(paciente, "/1/contenido"))
    assert r.status_code == 404
    assert r.json()["detail"] == "SALUTEM no entregó el contenido del archivo"


def test_el_auditor_puede_leer(as_auditor, paciente):
    assert as_auditor.get(_url(paciente)).status_code == 200


def test_sin_sesion_no_hay_acceso(client, paciente):
    assert client.get(_url(paciente)).status_code == 401
