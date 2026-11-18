"""QA-011: los motores de alertas de licencias (AlertaLicencia) y de fármacos (Alerta) y los casos cerrados."""

from datetime import date, timedelta

from sqlalchemy import select

from app.models.alerta_licencia import AlertaLicencia
from app.models.farmacos import Alerta, Receta, RegistroFarmacologico
from app.models.licencia import LicenciaMedica
from app.services.farmacos import generar_alertas_revision
from app.services.licencias_alerta import generar_alertas_vencimiento


def _ingreso(as_admin, rut, nombre):
    return as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": rut, "nombre": nombre, "sexo": "F", "edad": 33, "region": "Maule",
            "diagnostico": "x", "tipo_derivacion": "DIAT", "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio", "fecha_ingreso": "2026-06-01",
        },
    ).json()


def _licencia(db, ingreso_id, hoy):
    fin = hoy + timedelta(days=1)
    lm = LicenciaMedica(
        ingreso_id=ingreso_id, tipo_lm="1", tipo_reposo="total", fecha_inicio=hoy,
        fecha_termino=fin, fecha_emision=hoy, inicio_reposo=hoy, fin_reposo=fin,
        cantidad_dias=2, diagnostico="F32", anulada=False,
    )
    db.add(lm)
    db.flush()
    return lm


def _receta(db, ingreso_id, hoy):
    reg = RegistroFarmacologico(
        ingreso_id=ingreso_id, medico_tratante="Dr. X", estado_farmacologico="en_tratamiento"
    )
    db.add(reg)
    db.flush()
    r = Receta(
        registro_id=reg.id, fecha_emision=hoy, fecha_revision=hoy + timedelta(days=2),
        marca_medicamento="Sertralina",
    )
    db.add(r)
    db.flush()
    return r


def _cerrar(cli, ing_id):
    r = cli.patch(
        f"/api/v1/ingresos/{ing_id}/estado", json={"estado": "cerrado", "motivo_cierre": "abandono"}
    )
    assert r.status_code == 200, r.text


def test_cerrar_apaga_alertas_abiertas_de_licencia_y_farmacos(as_admin, db_session):
    hoy = date.today()
    ing = _ingreso(as_admin, "11.111.111-1", "Caso Uno")
    otro = _ingreso(as_admin, "22.222.222-2", "Caso Dos")
    lm, lm_otro = _licencia(db_session, ing["id"], hoy), _licencia(db_session, otro["id"], hoy)
    rc, rc_otro = _receta(db_session, ing["id"], hoy), _receta(db_session, otro["id"], hoy)
    generar_alertas_vencimiento(db_session, hoy, umbral_habiles=5, festivos=frozenset())
    generar_alertas_revision(db_session, hoy)
    assert db_session.scalars(select(AlertaLicencia).where(AlertaLicencia.licencia_id == lm.id)).one().activa
    assert not db_session.scalars(select(Alerta).where(Alerta.receta_id == rc.id)).one().leida

    _cerrar(as_admin, ing["id"])

    al = db_session.scalars(select(AlertaLicencia).where(AlertaLicencia.licencia_id == lm.id)).one()
    db_session.refresh(al)
    assert al.activa is False
    af = db_session.scalars(select(Alerta).where(Alerta.receta_id == rc.id)).one()
    db_session.refresh(af)
    assert af.leida is True
    # el otro caso sigue igual
    assert db_session.scalars(select(AlertaLicencia).where(AlertaLicencia.licencia_id == lm_otro.id)).one().activa
    assert not db_session.scalars(select(Alerta).where(Alerta.receta_id == rc_otro.id)).one().leida


def test_generadores_omiten_casos_cerrados_y_siguen_con_activos(as_admin, db_session):
    hoy = date.today()
    cerrado = _ingreso(as_admin, "11.111.111-1", "Caso Cerrado")
    activo = _ingreso(as_admin, "22.222.222-2", "Caso Activo")
    lm_c, lm_a = _licencia(db_session, cerrado["id"], hoy), _licencia(db_session, activo["id"], hoy)
    rc_c, rc_a = _receta(db_session, cerrado["id"], hoy), _receta(db_session, activo["id"], hoy)
    _cerrar(as_admin, cerrado["id"])

    nuevas_lm = generar_alertas_vencimiento(db_session, hoy, umbral_habiles=5, festivos=frozenset())
    nuevas_rc = generar_alertas_revision(db_session, hoy)

    assert [a.licencia_id for a in nuevas_lm] == [lm_a.id]
    assert [a.receta_id for a in nuevas_rc] == [rc_a.id]
    assert not list(db_session.scalars(select(AlertaLicencia).where(AlertaLicencia.licencia_id == lm_c.id)))
    assert not list(db_session.scalars(select(Alerta).where(Alerta.receta_id == rc_c.id)))
