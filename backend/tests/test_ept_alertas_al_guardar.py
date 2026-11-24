"""QA-009: las alertas de un caso EPT se generan al guardarlo, sin esperar al job diario."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alertas import AlertaNotif
from app.models.ept import PlazoEpt
from app.services.alertas import ejecutar_job_alertas

HOY = date.today()


def _crear_caso(as_admin, ingreso_id) -> int:
    r = as_admin.post(
        "/api/v1/casos-ept",
        json={
            "ingreso_id": ingreso_id,
            "fecha_ingreso_ept": (HOY - timedelta(days=10)).isoformat(),
            "eista": "Ana González",
            "factor_riesgo": "sobrecarga",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _alertas(db: Session, **filtros) -> list[AlertaNotif]:
    db.expire_all()
    consulta = select(AlertaNotif)
    for campo, valor in filtros.items():
        consulta = consulta.where(getattr(AlertaNotif, campo) == valor)
    return list(db.scalars(consulta))


def _plazo_id(db: Session, caso_id: int) -> int:
    return db.scalars(select(PlazoEpt.id).where(PlazoEpt.caso_ept_id == caso_id)).one()


def _plazos_hoy(as_admin, caso_id: int):
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={
            "caso_ept_id": caso_id,
            "plazo_informe_ept": HOY.isoformat(),
            "plazo_portal_isl": HOY.isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    return r


def test_plazos_que_vencen_hoy_generan_alertas_al_guardar(as_admin, ingreso_fixture, db_session):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    _plazos_hoy(as_admin, caso_id)
    alertas = _alertas(db_session, caso_tipo="ept", caso_id=_plazo_id(db_session, caso_id))
    assert {a.tipo for a in alertas} == {"plazo_ept", "plazo_isl"}
    assert {a.estado for a in alertas} == {"pendiente"}


def test_insumos_que_vencen_hoy_generan_alerta_al_guardar_el_proceso(
    as_admin, ingreso_fixture, db_session
):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/proceso",
        json={"caso_ept_id": caso_id, "plazo_insumos_empresa": HOY.isoformat()},
    )
    assert r.status_code == 201, r.text
    alertas = _alertas(db_session, caso_tipo="caso_ept", caso_id=caso_id)
    assert [a.tipo for a in alertas] == ["plazo_insumos_ept"]


def test_guardar_de_nuevo_y_el_job_no_duplican_alertas(as_admin, ingreso_fixture, db_session):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    _plazos_hoy(as_admin, caso_id)
    cuerpo = {"plazo_informe_ept": HOY.isoformat(), "plazo_portal_isl": HOY.isoformat()}
    as_admin.patch(f"/api/v1/casos-ept/{caso_id}/plazos", json=cuerpo)
    as_admin.patch(f"/api/v1/casos-ept/{caso_id}", json={"eista": "Otra persona"})
    ejecutar_job_alertas(db_session, actor="t", hoy=HOY)
    alertas = _alertas(db_session, caso_tipo="ept", caso_id=_plazo_id(db_session, caso_id))
    assert sorted(a.tipo for a in alertas) == ["plazo_ept", "plazo_isl"]


def test_mover_el_plazo_resuelve_la_alerta_anterior(as_admin, ingreso_fixture, db_session):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    _plazos_hoy(as_admin, caso_id)
    lejos = (HOY + timedelta(days=60)).isoformat()
    r = as_admin.patch(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"plazo_informe_ept": lejos, "plazo_portal_isl": lejos},
    )
    assert r.status_code == 200, r.text
    alertas = _alertas(db_session, caso_tipo="ept", caso_id=_plazo_id(db_session, caso_id))
    assert len(alertas) == 2
    assert {a.estado for a in alertas} == {"resuelta"}


def test_registrar_fecha_de_envio_resuelve_las_alertas(as_admin, ingreso_fixture, db_session):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    _plazos_hoy(as_admin, caso_id)
    r = as_admin.patch(
        f"/api/v1/casos-ept/{caso_id}/plazos", json={"fecha_envio": HOY.isoformat()}
    )
    assert r.status_code == 200, r.text
    alertas = _alertas(db_session, caso_tipo="ept", caso_id=_plazo_id(db_session, caso_id))
    assert len(alertas) == 2
    assert {a.estado for a in alertas} == {"resuelta"}


def test_plazos_lejanos_no_generan_alerta(as_admin, ingreso_fixture, db_session):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    lejos = (HOY + timedelta(days=60)).isoformat()
    as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"caso_ept_id": caso_id, "plazo_informe_ept": lejos, "plazo_portal_isl": lejos},
    )
    assert _alertas(db_session, caso_tipo="ept", caso_id=_plazo_id(db_session, caso_id)) == []
