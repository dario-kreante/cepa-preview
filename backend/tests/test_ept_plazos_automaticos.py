"""QA-005 (16-11): plazos EPT automáticos y alertas del día 18 al 20 (días corridos)."""

import datetime
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alertas import AlertaNotif
from app.models.ept import CasoEpt, PlazoEpt
from app.services.alertas import HitoPlazos, ejecutar_job_alertas, evaluar_plazos
from app.services.ept import plazos_automaticos
from tests.test_alertas_integracion import _make_ingreso


def test_plazos_automaticos_son_dias_corridos():
    # Cruza un fin de semana y feriados: igual cuenta corrido.
    informe, isl = plazos_automaticos(date(2026, 1, 10))
    assert informe == date(2026, 1, 28)  # ingreso + 18
    assert isl == date(2026, 1, 30)  # ingreso + 20 (último día de envío)


def _crear_caso(as_admin, ingreso_id, ingreso="2026-01-10"):
    r = as_admin.post(
        "/api/v1/casos-ept",
        json={
            "ingreso_id": ingreso_id,
            "mes": "Enero 2026",
            "fecha_ingreso_ept": ingreso,
            "nombre_trabajador": "Pedro Soto",
            "rut_trabajador": "12.345.678-5",
            "region_trabajador": "Maule",
            "eista": "Ana González",
            "factor_riesgo": "sobrecarga",
            "corresponde_ept": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_crear_plazos_vacios_los_calcula_el_backend(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(f"/api/v1/casos-ept/{caso_id}/plazos", json={"caso_ept_id": caso_id})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["plazo_informe_ept"] == "2026-01-28"
    assert body["plazo_portal_isl"] == "2026-01-30"


def test_crear_plazos_ajustados_se_respetan(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"caso_ept_id": caso_id, "plazo_informe_ept": "2026-02-01", "plazo_portal_isl": "2026-02-03"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["plazo_informe_ept"] == "2026-02-01"
    assert r.json()["plazo_portal_isl"] == "2026-02-03"


def test_crear_plazos_calcula_solo_el_campo_vacio(as_admin, ingreso_fixture):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    r = as_admin.post(
        f"/api/v1/casos-ept/{caso_id}/plazos",
        json={"caso_ept_id": caso_id, "plazo_informe_ept": "2026-02-01"},
    )
    assert r.json()["plazo_informe_ept"] == "2026-02-01"
    assert r.json()["plazo_portal_isl"] == "2026-01-30"


def test_actualizar_no_recalcula_plazos_existentes(as_admin, ingreso_fixture, db_session: Session):
    """Un caso antiguo sin plazos calculados no se rellena al editar otra cosa."""
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    db_session.add(PlazoEpt(caso_ept_id=caso_id))  # fila antigua: plazos vacíos
    db_session.commit()
    r = as_admin.patch(f"/api/v1/casos-ept/{caso_id}/plazos", json={"fecha_envio": "2026-01-25"})
    assert r.status_code == 200, r.text
    assert r.json()["plazo_informe_ept"] is None
    assert r.json()["plazo_portal_isl"] is None
    assert r.json()["fecha_envio"] == "2026-01-25"


# ── Alertas: del día 18 al 20 posterior al ingreso, hasta registrar el envío ──


def _hito(hoy_desde: date, hasta: date, tipo="plazo_ept", objetivo=None):
    return HitoPlazos(
        tipo=tipo, caso_id=1, caso_tipo="ept", usuario_id=None,
        plazo_objetivo=objetivo or hoy_desde, ventana_dias=5, usar_dias_habiles=True,
        desde=hoy_desde, hasta=hasta,
    )


def test_motor_hito_con_rango_solo_alerta_dentro_del_rango():
    h = _hito(date(2026, 1, 28), date(2026, 1, 30))
    assert evaluar_plazos([h], hoy=date(2026, 1, 27)) == []
    for dia in (28, 29, 30):
        assert len(evaluar_plazos([h], hoy=date(2026, 1, dia))) == 1
    assert evaluar_plazos([h], hoy=date(2026, 1, 31)) == []


def _caso_con_plazo(db: Session, *, envio=None, informe=date(2026, 1, 28), isl=date(2026, 1, 30)):
    ingreso = _make_ingreso(db, folio=f"F-P-{informe}-{envio}")
    caso = CasoEpt(
        ingreso_id=ingreso.id, mes="Enero 2026", fecha_ingreso_ept=date(2026, 1, 10),
        nombre_trabajador="P", rut_trabajador="11111111-1", region_trabajador="Maule",
        eista="E", factor_riesgo="sobrecarga", corresponde_ept=True,
    )
    db.add(caso)
    db.flush()
    plazo = PlazoEpt(
        caso_ept_id=caso.id, plazo_informe_ept=informe, plazo_portal_isl=isl, fecha_envio=envio
    )
    db.add(plazo)
    db.flush()
    return plazo


def _alertas(db, plazo):
    return set(
        db.scalars(
            select(AlertaNotif.tipo).where(AlertaNotif.caso_id == plazo.id, AlertaNotif.caso_tipo == "ept")
        )
    )


def test_job_no_alerta_antes_del_dia_18(db_session: Session):
    plazo = _caso_con_plazo(db_session)
    ejecutar_job_alertas(db_session, actor="t", hoy=date(2026, 1, 27))
    assert _alertas(db_session, plazo) == set()


def test_job_alerta_desde_el_dia_18_hasta_el_20(db_session: Session):
    plazo = _caso_con_plazo(db_session)
    ejecutar_job_alertas(db_session, actor="t", hoy=date(2026, 1, 28))
    assert _alertas(db_session, plazo) == {"plazo_ept", "plazo_isl"}


def test_job_alerta_el_dia_20_aunque_no_corrio_el_18(db_session: Session):
    plazo = _caso_con_plazo(db_session)
    ejecutar_job_alertas(db_session, actor="t", hoy=date(2026, 1, 30))
    assert _alertas(db_session, plazo) == {"plazo_ept", "plazo_isl"}


def test_job_no_alerta_pasado_el_dia_20(db_session: Session):
    plazo = _caso_con_plazo(db_session)
    ejecutar_job_alertas(db_session, actor="t", hoy=date(2026, 1, 31))
    assert _alertas(db_session, plazo) == set()


def test_job_no_alerta_si_ya_hay_envio(db_session: Session):
    plazo = _caso_con_plazo(db_session, envio=date(2026, 1, 20))
    ejecutar_job_alertas(db_session, actor="t", hoy=date(2026, 1, 29))
    assert _alertas(db_session, plazo) == set()


def test_registrar_envio_resuelve_las_alertas_abiertas(as_admin, ingreso_fixture, db_session: Session):
    caso_id = _crear_caso(as_admin, ingreso_fixture.id)
    as_admin.post(f"/api/v1/casos-ept/{caso_id}/plazos", json={"caso_ept_id": caso_id})
    plazo = db_session.scalars(select(PlazoEpt).where(PlazoEpt.caso_ept_id == caso_id)).one()
    ejecutar_job_alertas(db_session, actor="t", hoy=date(2026, 1, 29))
    assert _alertas(db_session, plazo) == {"plazo_ept", "plazo_isl"}

    r = as_admin.patch(f"/api/v1/casos-ept/{caso_id}/plazos", json={"fecha_envio": "2026-01-29"})
    assert r.status_code == 200, r.text
    db_session.expire_all()
    estados = set(
        db_session.scalars(
            select(AlertaNotif.estado).where(AlertaNotif.caso_id == plazo.id, AlertaNotif.caso_tipo == "ept")
        )
    )
    assert estados == {"resuelta"}


def test_plazos_legados_sin_plazo_isl_conservan_la_ventana_configurada(db_session: Session):
    """Sin plazo ISL no hay rango 18-20: rige la ventana de la configuración (comportamiento previo)."""
    hoy = datetime.date.today()
    plazo = _caso_con_plazo(db_session, informe=hoy + datetime.timedelta(days=1), isl=None)
    ejecutar_job_alertas(db_session, actor="t", hoy=hoy)
    assert _alertas(db_session, plazo) == {"plazo_ept"}
