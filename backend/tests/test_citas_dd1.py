"""Tests DD-1 (EPIC-09 rework): citas reales desde confirmar_citas + PATCH estado.

Cubre:
  TC-DD1-01: confirmar una propuesta crea filas Cita(estado=agendada) en la tabla de hechos.
  TC-DD1-02: PATCH /citas/{id}/estado transiciona agendada → realizada correctamente.
  TC-DD1-03: PATCH transición inválida devuelve 409.
  TC-DD1-04: integración end-to-end propuesta → confirmar → PATCH realizada → reporte operativo.
"""
import pytest
from datetime import date

from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def paciente_con_ingreso(db_session):
    pac = Paciente(
        rut="88888888-8", nombre="Test DD1", sexo="M", edad=35, region="Maule"
    )
    db_session.add(pac)
    db_session.flush()

    ing = Ingreso(
        paciente_id=pac.id,
        folio="F-DD1-001",
        folio_manual=True,
        programa="DIEP",
        tipo_convenio="DIEP",
        fecha_ingreso=date(2026, 1, 10),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Test DD1",
    )
    db_session.add(ing)
    db_session.flush()
    return {"paciente": pac, "ingreso": ing}


@pytest.fixture
def cita_agendada(db_session, paciente_con_ingreso):
    """Cita en estado 'agendada' directamente en tabla de hechos."""
    ing = paciente_con_ingreso["ingreso"]
    c = Cita(ingreso_id=ing.id, estado="agendada", fecha=date(2026, 3, 10))
    db_session.add(c)
    db_session.commit()
    return c


# ── TC-DD1-01: confirmar_citas crea Cita en tabla de hechos ──────────────────

def test_confirmar_citas_crea_cita_en_tabla_hechos(db_session, paciente_con_ingreso):
    """Al confirmar una CitaPropuesta se debe crear una Cita(estado=agendada)."""
    from app.agendamiento.models import CitaPropuesta, PropuestaAgenda
    from app.agendamiento.service import confirmar_citas
    from sqlalchemy import select

    pac = paciente_con_ingreso["paciente"]

    # Crear PropuestaAgenda y CitaPropuesta manualmente
    propuesta = PropuestaAgenda(
        profesional_id=1,
        tipo="diaria",
        fecha_inicio=date(2026, 3, 15),
        fecha_fin=date(2026, 3, 15),
        estado="borrador",
        generado_por="test",
    )
    db_session.add(propuesta)
    db_session.flush()

    cita_p = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=pac.id,
        fecha_candidata=date(2026, 3, 15),
        prioridad="control_vencido",
        razon="test",
        estado="propuesta",
    )
    db_session.add(cita_p)
    db_session.flush()

    antes = db_session.execute(
        select(Cita).where(Cita.ingreso_id == paciente_con_ingreso["ingreso"].id)
    ).scalars().all()

    confirmar_citas(db_session, propuesta.id, [cita_p.id], actor="test")
    db_session.flush()

    despues = db_session.execute(
        select(Cita).where(Cita.ingreso_id == paciente_con_ingreso["ingreso"].id)
    ).scalars().all()

    assert len(despues) == len(antes) + 1
    nueva = despues[-1]
    assert nueva.estado == "agendada"
    assert nueva.fecha == date(2026, 3, 15)


# ── TC-DD1-02: PATCH estado agendada → realizada ─────────────────────────────

def test_patch_estado_cita_agendada_a_realizada(as_coordinacion, cita_agendada):
    resp = as_coordinacion.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "realizada"
    assert body["id"] == cita_agendada.id


# ── TC-DD1-03: PATCH transición inválida devuelve 409 ─────────────────────────

def test_patch_estado_transicion_invalida_409(as_coordinacion, cita_agendada):
    """realizada → agendada no es una transición permitida."""
    # Primero pasamos a realizada
    as_coordinacion.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    # Luego intentamos volver a agendada
    resp = as_coordinacion.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "agendada"},
    )
    assert resp.status_code == 409


# ── TC-DD1-04: integración end-to-end propuesta→confirmar→PATCH→reporte ──────

def test_integracion_propuesta_confirmar_realizada_reporte(
    as_coordinacion, db_session, paciente_con_ingreso
):
    """
    Crea una Cita via confirmar_citas, la transiciona a 'realizada' vía PATCH,
    y verifica que el reporte operativo la contabiliza.
    """
    from app.agendamiento.models import CitaPropuesta, PropuestaAgenda
    from app.agendamiento.service import confirmar_citas

    pac = paciente_con_ingreso["paciente"]
    ing = paciente_con_ingreso["ingreso"]

    propuesta = PropuestaAgenda(
        profesional_id=2,
        tipo="diaria",
        fecha_inicio=date(2026, 3, 20),
        fecha_fin=date(2026, 3, 20),
        estado="borrador",
        generado_por="integ",
    )
    db_session.add(propuesta)
    db_session.flush()

    cita_p = CitaPropuesta(
        propuesta_id=propuesta.id,
        paciente_id=pac.id,
        fecha_candidata=date(2026, 3, 20),
        prioridad="control_vencido",
        razon="integ test",
        estado="propuesta",
    )
    db_session.add(cita_p)
    db_session.flush()

    confirmadas = confirmar_citas(db_session, propuesta.id, [cita_p.id], actor="integ")
    db_session.commit()

    assert len(confirmadas) == 1

    # Buscar la Cita creada
    from sqlalchemy import select
    citas_hecho = db_session.execute(
        select(Cita).where(Cita.ingreso_id == ing.id).where(Cita.estado == "agendada")
    ).scalars().all()
    assert len(citas_hecho) >= 1
    cita_id = citas_hecho[-1].id

    # PATCH a realizada
    resp = as_coordinacion.patch(
        f"/api/v1/citas/{cita_id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 200

    # Reporte operativo: debe contar esa cita
    resp_rep = as_coordinacion.get("/api/v1/reportes/operativo", params={
        "fecha_desde": "2026-03-01",
        "fecha_hasta": "2026-03-31",
    })
    assert resp_rep.status_code == 200
    body = resp_rep.json()
    assert body["totales"]["realizadas"] >= 1


# ── TC-DD1-05: PATCH sin auth devuelve 401 ───────────────────────────────────

def test_patch_cita_sin_auth(client, cita_agendada):
    resp = client.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 401


# ── TC-DD1-06: Auditor no puede PATCH (403) ───────────────────────────────────

def test_patch_cita_auditor_rechazado(as_auditor, cita_agendada):
    resp = as_auditor.patch(
        f"/api/v1/citas/{cita_agendada.id}/estado",
        json={"estado": "realizada"},
    )
    assert resp.status_code == 403
