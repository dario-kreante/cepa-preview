"""Configuración de alertas y festivos (COMP-2609-07) y job programado (COMP-2609-06).

TC-072-07: cambiar el umbral de licencias de 3 a 5 días hábiles cambia el resultado del
job sin reiniciar nada: el job lee la configuración de la BD en cada ejecución.
"""

import datetime

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.alerta_licencia import AlertaLicencia
from app.models.alertas import AlertaNotif
from app.models.audit_log import AuditLog
from app.models.config_alerta import ConfigAlerta, Festivo
from app.models.farmacos import Alerta
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.services.alertas import ejecutar_job_alertas
from app.services.alertas_job import correr_job_alertas
from app.services.licencias_alerta import generar_alertas_vencimiento

# Lunes 5 de octubre de 2026 (sin festivos esa semana; el 12 es lunes festivo).
LUNES = datetime.date(2026, 10, 5)


def _ingreso(db: Session, sufijo: str) -> Ingreso:
    pac = Paciente(rut=f"77{sufijo}", nombre="Config Alerta", sexo="M", edad=40, region="Maule")
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio=f"F-CFG-{sufijo}",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    return ing


def _licencia(db: Session, termino: datetime.date, sufijo: str) -> LicenciaMedica:
    ing = _ingreso(db, sufijo)
    inicio = termino - datetime.timedelta(days=14)
    lm = LicenciaMedica(
        ingreso_id=ing.id,
        tipo_lm="5",
        tipo_reposo="total",
        fecha_inicio=inicio,
        fecha_termino=termino,
        fecha_emision=inicio,
        inicio_reposo=inicio,
        fin_reposo=termino,
        cantidad_dias=15,
        diagnostico="F32.1",
        origen="sistema",
        envio_isl="pendiente",
        anulada=False,
    )
    db.add(lm)
    db.flush()
    return lm


def _alertas_licencia(db: Session, lm: LicenciaMedica) -> int:
    return db.scalar(
        select(func.count()).select_from(AlertaLicencia).where(AlertaLicencia.licencia_id == lm.id)
    )


# ── Migración sembrada ──────────────────────────────────────────────────────


def test_migracion_siembra_umbrales_actuales(db_session: Session):
    filas = {c.tipo: c for c in db_session.scalars(select(ConfigAlerta))}
    assert len(filas) == 8  # 7 de COMP-2609-07 + gaf_licencia (1300, desactivada)
    assert (filas["vencimiento_licencia"].dias, filas["vencimiento_licencia"].habiles) == (3, True)
    assert (filas["oda_por_vencer"].dias, filas["oda_por_vencer"].habiles) == (7, False)
    assert filas["consentimiento_pendiente"].dias == 30
    assert all(c.activo for t, c in filas.items() if t != "gaf_licencia")
    assert filas["gaf_licencia"].activo is False


def test_migracion_siembra_festivos_2026_2027(db_session: Session):
    fechas = set(db_session.scalars(select(Festivo.fecha)))
    assert datetime.date(2026, 9, 18) in fechas
    assert datetime.date(2026, 4, 3) in fechas  # Viernes Santo 2026
    assert datetime.date(2027, 3, 26) in fechas  # Viernes Santo 2027
    assert datetime.date(2027, 12, 25) in fechas


# ── TC-072-07 y festivos en el cálculo ───────────────────────────────────────


def test_tc_072_07_cambiar_umbral_licencias_cambia_resultado(as_coordinacion: TestClient, db_session):
    # Termina el viernes 9: 4 días hábiles desde el lunes 5.
    lm = _licencia(db_session, datetime.date(2026, 10, 9), "0707")

    generar_alertas_vencimiento(db_session, hoy=LUNES)
    assert _alertas_licencia(db_session, lm) == 0  # umbral 3 < 4

    resp = as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "vencimiento_licencia", "dias": 5, "habiles": True, "activo": True}],
    )
    assert resp.status_code == 200, resp.text

    generar_alertas_vencimiento(db_session, hoy=LUNES)
    assert _alertas_licencia(db_session, lm) == 1  # umbral 5 ≥ 4


def test_festivo_en_medio_cambia_conteo_habiles(as_coordinacion: TestClient, db_session):
    # Jueves 8: 3 días hábiles desde el lunes 5; con un festivo el miércoles 7, 2.
    lm = _licencia(db_session, datetime.date(2026, 10, 8), "0808")
    as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "vencimiento_licencia", "dias": 2, "habiles": True, "activo": True}],
    )
    generar_alertas_vencimiento(db_session, hoy=LUNES)
    assert _alertas_licencia(db_session, lm) == 0

    resp = as_coordinacion.post(
        "/api/v1/config-alertas/festivos",
        json={"fecha": "2026-10-07", "descripcion": "Festivo de prueba"},
    )
    assert resp.status_code == 201, resp.text

    nuevas = generar_alertas_vencimiento(db_session, hoy=LUNES)
    assert [a.dias_habiles_restantes for a in nuevas if a.licencia_id == lm.id] == [2]


def test_motor_lee_configuracion_y_respeta_inactivo(as_coordinacion: TestClient, db_session):
    ing = _ingreso(db_session, "0909")
    oda = Oda(
        ingreso_id=ing.id,
        identificador="ODA-CFG",
        fecha_vencimiento=LUNES + datetime.timedelta(days=10),
        vigente=True,
    )
    db_session.add(oda)
    db_session.flush()

    def alertas_oda() -> int:
        return db_session.scalar(
            select(func.count()).select_from(AlertaNotif).where(
                AlertaNotif.caso_id == oda.id, AlertaNotif.tipo == "oda_por_vencer"
            )
        )

    ejecutar_job_alertas(db_session, hoy=LUNES)
    assert alertas_oda() == 0  # ventana 7 < 10

    as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "oda_por_vencer", "dias": 12, "habiles": False, "activo": False}],
    )
    ejecutar_job_alertas(db_session, hoy=LUNES)
    assert alertas_oda() == 0  # inactivo: no genera

    as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "oda_por_vencer", "dias": 12, "habiles": False, "activo": True}],
    )
    ejecutar_job_alertas(db_session, hoy=LUNES)
    assert alertas_oda() == 1


def test_tabla_vacia_usa_valores_por_defecto(db_session: Session):
    db_session.execute(delete(ConfigAlerta))
    lm = _licencia(db_session, datetime.date(2026, 10, 8), "1010")  # 3 hábiles
    generar_alertas_vencimiento(db_session, hoy=LUNES)
    assert _alertas_licencia(db_session, lm) == 1


# ── Endpoints y RBAC ────────────────────────────────────────────────────────


def test_get_config_lectura_por_roles(as_admin: TestClient, as_auditor: TestClient):
    for cliente in (as_admin, as_auditor):
        resp = cliente.get("/api/v1/config-alertas")
        assert resp.status_code == 200
        tipos = {c["tipo"] for c in resp.json()}
        assert "vencimiento_licencia" in tipos and len(tipos) == 8
        assert cliente.get("/api/v1/config-alertas/festivos").status_code == 200


def test_escritura_solo_coordinacion(as_admin: TestClient, as_auditor: TestClient):
    cuerpo = [{"tipo": "plazo_ept", "dias": 9, "habiles": True, "activo": True}]
    for cliente in (as_admin, as_auditor):
        assert cliente.put("/api/v1/config-alertas", json=cuerpo).status_code == 403
        assert (
            cliente.post(
                "/api/v1/config-alertas/festivos", json={"fecha": "2026-12-31", "descripcion": "x"}
            ).status_code
            == 403
        )


def test_put_valida_tipo_y_dias(as_coordinacion: TestClient):
    malo = as_coordinacion.put(
        "/api/v1/config-alertas", json=[{"tipo": "inventado", "dias": 3, "habiles": True, "activo": True}]
    )
    assert malo.status_code == 422
    negativo = as_coordinacion.put(
        "/api/v1/config-alertas", json=[{"tipo": "plazo_ept", "dias": -1, "habiles": True, "activo": True}]
    )
    assert negativo.status_code == 422


def test_put_y_festivos_quedan_auditados(as_coordinacion: TestClient, db_session: Session):
    as_coordinacion.put(
        "/api/v1/config-alertas",
        json=[{"tipo": "plazo_isl", "dias": 8, "habiles": True, "activo": True}],
    )
    creado = as_coordinacion.post(
        "/api/v1/config-alertas/festivos", json={"fecha": "2026-12-31", "descripcion": "Prueba"}
    )
    assert creado.status_code == 201
    duplicado = as_coordinacion.post(
        "/api/v1/config-alertas/festivos", json={"fecha": "2026-12-31", "descripcion": "Otra"}
    )
    assert duplicado.status_code == 409
    borrado = as_coordinacion.delete(f"/api/v1/config-alertas/festivos/{creado.json()['id']}")
    assert borrado.status_code == 204

    entidades = [
        (t.entity, t.action)
        for t in db_session.scalars(select(AuditLog).where(AuditLog.actor == "coord_test"))
    ]
    assert ("config_alerta", "UPDATE") in entidades
    assert ("festivo", "CREATE") in entidades
    assert ("festivo", "DELETE") in entidades


# ── Job programado (COMP-2609-06) ────────────────────────────────────────────


def test_job_completo_idempotente_y_actor_sistema(db_session: Session):
    lm = _licencia(db_session, datetime.date(2026, 10, 7), "1111")  # 2 hábiles
    ing = _ingreso(db_session, "1112")
    db_session.add(
        Oda(ingreso_id=ing.id, identificador="ODA-JOB", fecha_vencimiento=LUNES + datetime.timedelta(days=3), vigente=True)
    )
    db_session.flush()

    primero = correr_job_alertas(db_session, hoy=LUNES)
    assert primero["motor"] >= 2  # ODA + licencia en alerta_notif
    assert primero["licencias"] >= 1

    segundo = correr_job_alertas(db_session, hoy=LUNES)
    assert segundo == {"motor": 0, "licencias": 0, "recetas": 0}
    assert _alertas_licencia(db_session, lm) == 1

    actores = set(
        db_session.scalars(
            select(AuditLog.actor).where(AuditLog.entity.in_(["alerta_notif", "alerta_licencia"]))
        )
    )
    assert actores == {"sistema"}
    # La tabla de recetas no se toca si no hay recetas; solo se asegura que exista la cuenta.
    assert db_session.scalar(select(func.count()).select_from(Alerta)) is not None


def test_script_cli_imprime_resumen_y_sale_con_cero(db_session: Session, monkeypatch, capsys, tmp_path):
    from contextlib import contextmanager

    from app.scripts import alertas_job

    @contextmanager
    def _sesion():
        yield db_session

    monkeypatch.setattr(alertas_job, "SessionLocal", _sesion)
    codigo = alertas_job.main(["--log", str(tmp_path / "alertas.log")])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "motor=" in salida and "licencias=" in salida and "recetas=" in salida
    assert (tmp_path / "alertas.log").read_text(encoding="utf-8")


def test_script_cli_falla_con_codigo_uno(monkeypatch, tmp_path):
    from app.scripts import alertas_job

    def _explota():
        raise RuntimeError("sin BD")

    monkeypatch.setattr(alertas_job, "SessionLocal", _explota)
    assert alertas_job.main(["--log", str(tmp_path / "a.log")]) == 1
