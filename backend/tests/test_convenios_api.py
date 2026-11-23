"""API del mantenedor de convenios: catálogo, actualización desde SALUTEM y sugerencia por origen."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.integrations.salutem.errors import SalutemUnavailableError
from app.models.audit_log import AuditLog
from app.models.convenio import Convenio
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemPersona
from app.services.salutem_sync.profesionales import normalizar_nombre
from tests.salutem_falso import SalutemFalso

AHORA = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
URL = "/api/v1/convenios"


def _convenio(db, nombre, *, salutem_id=None, visible=True, activo=True) -> Convenio:
    c = Convenio(nombre=nombre, nombre_normalizado=normalizar_nombre(nombre), salutem_id=salutem_id,
                 visible=visible, activo_salutem=activo)
    db.add(c)
    db.flush()
    return c


def _persona(db, salutem_id, rut, origen) -> SalutemPersona:
    p = SalutemPersona(salutem_id=salutem_id, rut=rut, contenido={"origen": origen}, hash_contenido="x",
                       visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA)
    db.add(p)
    db.flush()
    return p


def test_listar_lo_ven_los_tres_roles(as_auditor):
    assert as_auditor.get(URL).status_code == 200


def test_listar_solo_seleccionables(as_admin, db_session):
    _convenio(db_session, "Convenio B")
    _convenio(db_session, "Convenio A")
    _convenio(db_session, "Oculto", visible=False)
    _convenio(db_session, "Inactivo", salutem_id=9, activo=False)
    todos = as_admin.get(URL).json()
    assert [c["nombre"] for c in todos] == ["Convenio A", "Convenio B", "Inactivo", "Oculto"]
    sel = as_admin.get(URL, params={"solo_seleccionables": True}).json()
    assert [c["nombre"] for c in sel] == ["Convenio A", "Convenio B"]


def test_auditor_no_puede_crear(as_auditor):
    assert as_auditor.post(URL, json={"nombre": "Nuevo"}).status_code == 403


def test_crear_ok_audita(as_admin, db_session):
    r = as_admin.post(URL, json={"nombre": "  Convenio   Nuevo "})
    assert r.status_code == 201
    assert r.json()["nombre"] == "Convenio Nuevo"
    assert r.json()["salutem_id"] is None
    assert r.json()["seleccionable"] is True
    assert db_session.scalar(select(AuditLog).where(AuditLog.action == "convenio_creado")) is not None


def test_crear_duplicado_por_tildes_409(as_admin):
    assert as_admin.post(URL, json={"nombre": "Convenio Inglés"}).status_code == 201
    assert as_admin.post(URL, json={"nombre": "convenio ingles"}).status_code == 409


def test_no_se_renombra_uno_de_salutem(as_admin, db_session):
    c = _convenio(db_session, "Convenio ISL", salutem_id=1486)
    r = as_admin.patch(f"{URL}/{c.id}", json={"nombre": "Otro"})
    assert r.status_code == 422
    assert "SALUTEM" in r.json()["detail"]


def test_renombrar_manual_y_choque(as_admin, db_session):
    a = _convenio(db_session, "Manual A")
    _convenio(db_session, "Manual B")
    assert as_admin.patch(f"{URL}/{a.id}", json={"nombre": "manual b"}).status_code == 409
    r = as_admin.patch(f"{URL}/{a.id}", json={"nombre": "Manual C"})
    assert r.status_code == 200 and r.json()["nombre"] == "Manual C"


def test_patch_inexistente_404(as_admin):
    assert as_admin.patch(f"{URL}/999999", json={"visible": False}).status_code == 404


def test_ocultar(as_coordinacion, db_session):
    c = _convenio(db_session, "Convenio SSM")
    r = as_coordinacion.patch(f"{URL}/{c.id}", json={"visible": False})
    assert r.status_code == 200
    assert r.json()["visible"] is False and r.json()["seleccionable"] is False
    assert db_session.scalar(select(AuditLog).where(AuditLog.entity == "convenio")) is not None


def test_actualizar_salutem_ok(as_admin, db_session, monkeypatch):
    falso = SalutemFalso()
    falso.convenios = [{"id": 1486, "nombre": "Convenio ISL Maule", "activo": True}]
    monkeypatch.setattr("app.routers.convenios.get_salutem_client", lambda: falso)
    r = as_admin.post(f"{URL}/actualizar-salutem")
    assert r.status_code == 200
    assert r.json()["creados"] == 1
    assert db_session.scalar(select(Convenio).where(Convenio.salutem_id == 1486)) is not None


def test_actualizar_salutem_caido_502(as_admin, db_session, monkeypatch):
    class Cliente:
        def listar_convenios(self):
            raise SalutemUnavailableError("HTTP 504")

    monkeypatch.setattr("app.routers.convenios.get_salutem_client", lambda: Cliente())
    r = as_admin.post(f"{URL}/actualizar-salutem")
    assert r.status_code == 502
    assert r.json()["detail"] == "SALUTEM no respondió; intenta más tarde."
    assert db_session.scalars(select(Convenio)).all() == []


def test_auditor_no_actualiza_salutem(as_auditor):
    assert as_auditor.post(f"{URL}/actualizar-salutem").status_code == 403


def test_para_reportes_incluye_valores_antiguos(as_admin, db_session):
    _convenio(db_session, "Convenio SSM")
    p = Paciente(rut="390001185", nombre="X", sexo="M", edad=50, region="Maule")
    db_session.add(p)
    db_session.flush()
    for folio, tipo in (("F-1", "ISL"), ("F-2", "ISL"), ("F-3", "Convenio SSM"), ("F-4", "")):
        db_session.add(Ingreso(paciente_id=p.id, folio=folio, folio_manual=True, fecha_ingreso=date(2026, 9, 1),
                               tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
                               diagnostico="prueba", estado="activo", tipo_convenio=tipo))
    db_session.flush()
    assert as_admin.get(f"{URL}/para-reportes").json() == ["Convenio SSM", "ISL"]


def test_sugerido_por_paciente_ignora_mayusculas(as_admin, db_session):
    _persona(db_session, 500, "390001185", "Convenio ISL Maule")
    db_session.add(Paciente(rut="390001185", nombre="X", sexo="M", edad=50, region="Maule",
                            salutem_persona_id=500))
    c = _convenio(db_session, "Convenio ISL MAULE")
    pac = db_session.scalar(select(Paciente))
    r = as_admin.get(f"{URL}/sugerido", params={"paciente_id": pac.id})
    assert r.status_code == 200
    assert r.json()["convenio"]["id"] == c.id


def test_sugerido_por_rut(as_admin, db_session):
    _persona(db_session, 501, "390001185", "Convenio ISL Maule")
    c = _convenio(db_session, "Convenio ISL Maule")
    r = as_admin.get(f"{URL}/sugerido", params={"rut": "39.000.118-5"})
    assert r.json()["convenio"]["id"] == c.id


def test_sugerido_sin_origen_es_null(as_admin, db_session):
    _persona(db_session, 502, "390001185", "Sin Origen")
    _convenio(db_session, "Sin Origen")
    assert as_admin.get(f"{URL}/sugerido", params={"rut": "390001185"}).json() == {"convenio": None}


def test_sugerido_rut_invalido_o_sin_persona_es_null(as_admin):
    assert as_admin.get(f"{URL}/sugerido", params={"rut": "abc"}).json() == {"convenio": None}
    assert as_admin.get(f"{URL}/sugerido", params={"rut": "390001185"}).json() == {"convenio": None}
    assert as_admin.get(f"{URL}/sugerido").json() == {"convenio": None}


def test_sugerido_convenio_oculto_es_null(as_admin, db_session):
    _persona(db_session, 503, "390001185", "Convenio ISL Maule")
    _convenio(db_session, "Convenio ISL Maule", visible=False)
    assert as_admin.get(f"{URL}/sugerido", params={"rut": "390001185"}).json() == {"convenio": None}
