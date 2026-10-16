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

    # Se compara como conjunto: el orden por nombre depende del collation de la BD.
    filas = db_session.scalars(select(Profesional)).all()
    assert {(p.nombre, p.origen, p.activo) for p in filas} == {
        ("Dr. Luis Soto", "SALUTEM", True),
        ("Dra. Ana Rojas", "SALUTEM", True),
    }
    assert len(filas) == 2


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
    assert primera.json()["creados"] == 1
    assert as_admin.post("/api/v1/profesionales/importar-salutem").json()["creados"] == 0

    baja = db_session.scalar(select(Profesional).where(Profesional.nombre == "Dr. Dado De Baja"))
    assert baja.activo is False
    nueva = db_session.scalar(select(Profesional).where(Profesional.nombre == "Dra. Nueva Salutem"))
    assert nueva.origen == "SALUTEM"


def test_importar_salutem_ejecuta_el_paso_completo_del_sync(as_admin: TestClient, db_session: Session):
    from app.integrations.salutem.models import AtencionSalutem
    from app.services.salutem_sync import copia
    from datetime import datetime, timezone

    ahora = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)
    copia.guardar_atencion(db_session, AtencionSalutem.desde_api({
        "personaId": 1, "citaId": 5, "citaFecha": "2026-09-01", "estadoCitaId": 3,
        "especialidadNombre": "Médico/a", "profesionalId": 3090,
        "profesionalNombre": "DRA. PAULA ROJAS", "sucursalNombre": "Talca",
    }), ahora)
    db_session.flush()

    resp = as_admin.post("/api/v1/profesionales/importar-salutem")

    assert resp.status_code == 200
    body = resp.json()
    assert (body["creados"], body["actualizados"], body["adoptados"], body["vinculados"]) == (1, 0, 0, 0)
    assert body["errores"] == []
    listado = as_admin.get("/api/v1/profesionales").json()
    [p] = [x for x in listado if x["salutem_profesional_id"] == 3090]
    assert p["especialidades"] == ["Médico/a"]
    assert p["sucursales"] == ["Talca"]
    assert p["sincronizado_en"] is not None


def _actividad_fixture(db: Session) -> Profesional:
    from app.models.ficha_clinica import FichaClinica

    prof = Profesional(
        nombre="Dra. Actividad", origen="SALUTEM", activo=True, salutem_profesional_id=4001,
        primera_atencion=datetime.date(2026, 8, 1), ultima_atencion=datetime.date(2026, 9, 10),
    )
    db.add(prof)
    db.flush()
    _control(db, "21", "Dra. Actividad")
    ctrl = db.scalar(select(ControlMedico).where(ControlMedico.medico_tratante == "Dra. Actividad"))
    ctrl.profesional_id = prof.id
    ing = db.get(Ingreso, ctrl.ingreso_id)
    for n, (fecha, esp, estado) in enumerate([
        ("2026-08-01", "Médico/a", 3), ("2026-09-10", "Evaluación médica", 3),
        ("2026-09-05", "Médico/a", 3), ("2026-09-20", "Médico/a", 1),
    ]):
        db.add(FichaClinica(
            ingreso_id=ing.id, folio=ing.folio, origen="SALUTEM", salutem_cita_id=900 + n,
            profesional_id=prof.id,
            contenido={"citaFecha": fecha, "especialidadNombre": esp, "estadoCitaId": estado},
        ))
    db.flush()
    return prof


def test_actividad_del_profesional(as_auditor: TestClient, db_session: Session):
    prof = _actividad_fixture(db_session)

    resp = as_auditor.get(f"/api/v1/profesionales/{prof.id}/actividad")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_atenciones"] == 3  # la agendada (estado 1) no cuenta
    assert body["atenciones_por_especialidad"] == [
        {"especialidad": "Médico/a", "total": 2}, {"especialidad": "Evaluación médica", "total": 1},
    ]
    assert body["total_controles"] == 1
    assert body["pacientes_distintos"] == 1
    assert (body["primera_atencion"], body["ultima_atencion"]) == ("2026-08-01", "2026-09-10")
    assert [a["fecha"] for a in body["ultimas_atenciones"]] == ["2026-09-10", "2026-09-05", "2026-08-01"]
    primera = body["ultimas_atenciones"][0]
    assert primera["especialidad"] == "Evaluación médica"
    assert primera["folio"] == "F-PROF-21"
    assert primera["paciente"] == "Paciente Prof"
    assert {"ingreso_id", "paciente_id"} <= set(primera)


def test_actividad_limita_a_las_ultimas_20(as_admin: TestClient, db_session: Session):
    from app.models.ficha_clinica import FichaClinica

    prof = _actividad_fixture(db_session)
    ing = db_session.scalar(select(Ingreso).where(Ingreso.folio == "F-PROF-21"))
    for n in range(25):
        db_session.add(FichaClinica(
            ingreso_id=ing.id, folio=ing.folio, origen="SALUTEM", salutem_cita_id=1000 + n,
            profesional_id=prof.id,
            contenido={"citaFecha": "2026-09-11", "especialidadNombre": "Médico/a", "estadoCitaId": 3},
        ))
    db_session.flush()

    body = as_admin.get(f"/api/v1/profesionales/{prof.id}/actividad").json()

    assert body["total_atenciones"] == 28
    assert len(body["ultimas_atenciones"]) == 20


def test_actividad_sin_datos_y_404(as_admin: TestClient):
    pid = as_admin.post("/api/v1/profesionales", json={"nombre": "Dr. Sin Actividad"}).json()["id"]
    body = as_admin.get(f"/api/v1/profesionales/{pid}/actividad").json()
    assert body["total_atenciones"] == 0 and body["ultimas_atenciones"] == []
    assert body["atenciones_por_especialidad"] == [] and body["total_controles"] == 0
    assert as_admin.get("/api/v1/profesionales/999999/actividad").status_code == 404


def test_control_manual_con_profesional_id_usa_su_nombre(as_admin: TestClient, db_session: Session):
    _control(db_session, "31", "Dr. Base")
    ing = db_session.scalar(select(Ingreso).where(Ingreso.folio == "F-PROF-31"))
    prof = Profesional(nombre="Dra. Del Catálogo", origen="SIGE", activo=True)
    db_session.add(prof)
    db_session.flush()

    resp = as_admin.post("/api/v1/controles-medicos", json={
        "ingreso_id": ing.id, "fecha_control": "2026-09-02", "region_derivacion": "Maule",
        "profesional_id": prof.id,
    })

    assert resp.status_code == 201
    body = resp.json()
    assert (body["profesional_id"], body["medico_tratante"]) == (prof.id, "Dra. Del Catálogo")


def test_control_manual_respeta_el_medico_tratante_enviado(as_admin: TestClient, db_session: Session):
    _control(db_session, "32", "Dr. Base")
    ing = db_session.scalar(select(Ingreso).where(Ingreso.folio == "F-PROF-32"))
    prof = Profesional(nombre="Dra. Catálogo Dos", origen="SIGE", activo=True)
    db_session.add(prof)
    db_session.flush()

    body = as_admin.post("/api/v1/controles-medicos", json={
        "ingreso_id": ing.id, "fecha_control": "2026-09-02", "region_derivacion": "Maule",
        "profesional_id": prof.id, "medico_tratante": "Nombre escrito",
    }).json()

    assert (body["profesional_id"], body["medico_tratante"]) == (prof.id, "Nombre escrito")


def test_control_manual_valida_profesional_y_exige_algun_medico(as_admin: TestClient, db_session: Session):
    _control(db_session, "33", "Dr. Base")
    ing = db_session.scalar(select(Ingreso).where(Ingreso.folio == "F-PROF-33"))
    base = {"ingreso_id": ing.id, "fecha_control": "2026-09-02", "region_derivacion": "Maule"}

    assert as_admin.post("/api/v1/controles-medicos", json={**base, "profesional_id": 999999}).status_code == 404
    assert as_admin.post("/api/v1/controles-medicos", json=base).status_code == 422
    sin_id = as_admin.post("/api/v1/controles-medicos", json={**base, "medico_tratante": "Dr. Solo Texto"})
    assert sin_id.status_code == 201 and sin_id.json()["profesional_id"] is None
