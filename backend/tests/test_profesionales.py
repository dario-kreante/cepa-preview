"""Catálogo de profesionales para el agendamiento (siembra SALUTEM + CRUD)."""

import datetime
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.profesional import Profesional


def _control(db: Session, sufijo: str, medico: str, origen: str = "SALUTEM") -> None:
    pac = Paciente(rut=f"77{sufijo}", nombre="Paciente Prof", sexo="F", edad=40, region="Maule")
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio=f"F-PROF-{sufijo}",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 5),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    db.add(
        ControlMedico(
            ingreso_id=ing.id,
            fecha_control=datetime.date(2026, 9, 1),
            semana_control=1,
            medico_tratante=medico,
            region_derivacion="Maule",
            origen=origen,
        )
    )
    db.flush()


def _migracion_1340():
    ruta = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "1340_profesional.py"
    spec = importlib.util.spec_from_file_location("mig_1340", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_siembra_de_la_migracion_toma_medicos_salutem_distintos(db_session: Session):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    _control(db_session, "01", "Dra. Ana Rojas")
    _control(db_session, "02", "Dra. Ana Rojas")
    _control(db_session, "03", "Dr. Luis Soto")
    _control(db_session, "04", "Sin profesional informado")
    _control(db_session, "05", "Dr. Manual Cepa", origen="CEPA")
    db_session.execute(Profesional.__table__.delete())

    mig = _migracion_1340()
    ctx = MigrationContext.configure(db_session.connection())
    with Operations.context(ctx):
        mig._sembrar()

    filas = db_session.scalars(select(Profesional).order_by(Profesional.nombre)).all()
    assert [(p.nombre, p.origen, p.activo) for p in filas] == [
        ("Dr. Luis Soto", "SALUTEM", True),
        ("Dra. Ana Rojas", "SALUTEM", True),
    ]


def test_listar_lo_pueden_ver_los_tres_roles(as_auditor: TestClient, db_session: Session):
    db_session.add(Profesional(nombre="Dr. Visible", origen="SIGE", activo=True))
    db_session.flush()
    resp = as_auditor.get("/api/v1/profesionales")
    assert resp.status_code == 200
    assert "Dr. Visible" in [p["nombre"] for p in resp.json()]


def test_listar_solo_activos(as_admin: TestClient, db_session: Session):
    db_session.add_all([
        Profesional(nombre="Dr. Activo", origen="SIGE", activo=True),
        Profesional(nombre="Dr. Inactivo", origen="SIGE", activo=False),
    ])
    db_session.flush()
    nombres = [p["nombre"] for p in as_admin.get("/api/v1/profesionales?solo_activos=true").json()]
    assert "Dr. Activo" in nombres
    assert "Dr. Inactivo" not in nombres


def test_crear_limpia_espacios_y_queda_origen_sige(as_admin: TestClient):
    resp = as_admin.post(
        "/api/v1/profesionales", json={"nombre": "  Dra.  Paz   Muñoz ", "especialidad": "Psiquiatría"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre"] == "Dra. Paz Muñoz"
    assert body["especialidad"] == "Psiquiatría"
    assert body["origen"] == "SIGE"
    assert body["activo"] is True


def test_crear_nombre_duplicado_409(as_coordinacion: TestClient):
    assert as_coordinacion.post("/api/v1/profesionales", json={"nombre": "Dr. Doble"}).status_code == 201
    resp = as_coordinacion.post("/api/v1/profesionales", json={"nombre": "Dr. Doble"})
    assert resp.status_code == 409


def test_crear_nombre_vacio_422(as_admin: TestClient):
    assert as_admin.post("/api/v1/profesionales", json={"nombre": "   "}).status_code == 422


def test_auditor_no_puede_crear(as_auditor: TestClient):
    assert as_auditor.post("/api/v1/profesionales", json={"nombre": "Dr. X"}).status_code == 403


def test_editar_y_desactivar(as_admin: TestClient):
    pid = as_admin.post("/api/v1/profesionales", json={"nombre": "Dr. Editable"}).json()["id"]
    resp = as_admin.patch(
        f"/api/v1/profesionales/{pid}",
        json={"nombre": "Dr. Editado", "especialidad": "Medicina general", "activo": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert (body["nombre"], body["especialidad"], body["activo"]) == (
        "Dr. Editado", "Medicina general", False,
    )


def test_editar_sin_nombre_no_lo_cambia(as_admin: TestClient):
    pid = as_admin.post("/api/v1/profesionales", json={"nombre": "Dr. Fijo"}).json()["id"]
    resp = as_admin.patch(f"/api/v1/profesionales/{pid}", json={"activo": False})
    assert resp.json()["nombre"] == "Dr. Fijo"


def test_editar_a_nombre_existente_409(as_admin: TestClient):
    as_admin.post("/api/v1/profesionales", json={"nombre": "Dr. Uno"})
    pid = as_admin.post("/api/v1/profesionales", json={"nombre": "Dr. Dos"}).json()["id"]
    resp = as_admin.patch(f"/api/v1/profesionales/{pid}", json={"nombre": "Dr. Uno"})
    assert resp.status_code == 409


def test_editar_inexistente_404(as_admin: TestClient):
    assert as_admin.patch("/api/v1/profesionales/999999", json={"activo": False}).status_code == 404


def test_importar_salutem_es_idempotente_y_respeta_bajas(as_admin: TestClient, db_session: Session):
    _control(db_session, "11", "Dra. Nueva Salutem")
    _control(db_session, "12", "Dr. Dado De Baja")
    _control(db_session, "13", "Sin profesional informado")
    db_session.add(Profesional(nombre="Dr. Dado De Baja", origen="SALUTEM", activo=False))
    db_session.flush()

    primera = as_admin.post("/api/v1/profesionales/importar-salutem")
    assert primera.status_code == 200
    assert primera.json() == {"creados": 1}
    assert as_admin.post("/api/v1/profesionales/importar-salutem").json() == {"creados": 0}

    baja = db_session.scalar(select(Profesional).where(Profesional.nombre == "Dr. Dado De Baja"))
    assert baja.activo is False
    nueva = db_session.scalar(select(Profesional).where(Profesional.nombre == "Dra. Nueva Salutem"))
    assert nueva.origen == "SALUTEM"
