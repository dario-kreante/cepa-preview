"""QA-011: cierre del caso con motivo (lista propia, separada de tipo_alta) y reapertura."""

from datetime import date, datetime, time, timezone

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.domain.enums import MotivoCierre
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import AlertaNotif
from app.models.consentimiento import Consentimiento
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.services.alertas import ejecutar_job_alertas


def _ingreso(as_admin, **over):
    base = {
        "rut": "11.111.111-1",
        "nombre": "Ana González",
        "sexo": "F",
        "edad": 33,
        "region": "Maule",
        "diagnostico": "x",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-01",
    }
    base.update(over)
    return as_admin.post("/api/v1/ingresos", json=base).json()


def _patch(cli, ing_id, **body):
    return cli.patch(f"/api/v1/ingresos/{ing_id}/estado", json=body)


def test_motivos_son_los_seis_acordados():
    assert [m.value for m in MotivoCierre] == [
        "reca_ec",
        "alta_medica",
        "alta_administrativa",
        "abandono",
        "desiste_proceso",
        "cambio_prestador",
    ]


# ── PATCH /estado ──────────────────────────────────────────────────────────────
def test_cerrar_exige_motivo(as_admin):
    ing = _ingreso(as_admin)
    r = _patch(as_admin, ing["id"], estado="cerrado")
    assert r.status_code == 422
    assert as_admin.get(f"/api/v1/ingresos/{ing['id']}").json()["estado"] == "activo"


def test_motivo_fuera_de_lista_es_422(as_admin):
    ing = _ingreso(as_admin)
    assert _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="otro").status_code == 422


def test_cerrar_guarda_motivo_fecha_y_usuario(as_admin):
    ing = _ingreso(as_admin)
    r = _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="alta_medica")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "cerrado"
    assert cuerpo["motivo_cierre"] == "alta_medica"
    assert cuerpo["cierre_usuario"] == "admin_test"
    assert cuerpo["fecha_cierre"] is not None
    # no toca el tipo de alta existente
    assert cuerpo["tipo_alta"] is None


def test_cerrar_deja_auditoria(as_admin, db_session):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    filas = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "ingreso", AuditLog.entity_id == str(ing["id"]))
    ).all()
    assert any("abandono" in (f.valor_nuevo or "") for f in filas)


def test_encuadre_tambien_se_cierra(as_admin):
    ing = _ingreso(as_admin)
    assert _patch(as_admin, ing["id"], estado="encuadre").status_code == 200
    r = _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="desiste_proceso")
    assert r.status_code == 200
    assert r.json()["estado"] == "cerrado"


def test_motivo_en_estado_no_cerrado_es_422(as_admin):
    ing = _ingreso(as_admin)
    r = _patch(as_admin, ing["id"], estado="encuadre", motivo_cierre="abandono")
    assert r.status_code == 422


def test_cerrar_un_caso_ya_cerrado_es_409(as_admin):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    r = _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="alta_medica")
    assert r.status_code == 409


def test_auditor_no_cierra(as_admin, as_auditor):
    ing = _ingreso(as_admin)
    r = _patch(as_auditor, ing["id"], estado="cerrado", motivo_cierre="abandono")
    assert r.status_code == 403


# ── Reapertura ─────────────────────────────────────────────────────────────────
def test_administrativo_no_reabre(as_admin):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    r = _patch(as_admin, ing["id"], estado="activo")
    assert r.status_code == 403
    assert as_admin.get(f"/api/v1/ingresos/{ing['id']}").json()["estado"] == "cerrado"


def test_administrativo_no_reabre_por_otros_estados(as_admin):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    assert _patch(as_admin, ing["id"], estado="encuadre").status_code == 403
    assert _patch(as_admin, ing["id"], estado="derivado").status_code == 403


def test_coordinacion_reabre_limpia_cierre_y_audita(as_admin, as_coordinacion, db_session):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="alta_medica")
    r = _patch(as_coordinacion, ing["id"], estado="activo")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "activo"
    assert cuerpo["motivo_cierre"] is None
    assert cuerpo["fecha_cierre"] is None
    assert cuerpo["cierre_usuario"] is None
    filas = db_session.scalars(
        select(AuditLog).where(AuditLog.entity == "ingreso", AuditLog.entity_id == str(ing["id"]))
    ).all()
    reapertura = [f for f in filas if f.actor == "coord_test" and "alta_medica" in (f.valor_anterior or "")]
    assert reapertura, "la reapertura debe dejar el motivo anterior en la auditoría"


def test_superadmin_reabre(as_admin, as_superadmin):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    assert _patch(as_superadmin, ing["id"], estado="activo").status_code == 200


# ── POST /cierre (vía CEPA-014) ────────────────────────────────────────────────
def test_post_cierre_exige_motivo_al_cerrar(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "cerrado"})
    assert r.status_code == 422


def test_post_cierre_con_motivo_conserva_tipo_alta(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "motivo_cierre": "reca_ec", "tipo_alta": "medica"},
    )
    assert r.status_code == 200
    assert r.json()["motivo_cierre"] == "reca_ec"
    assert r.json()["tipo_alta"] == "medica"
    assert r.json()["cierre_usuario"] == "admin_test"


def test_post_cierre_derivado_no_pide_motivo(as_admin):
    ing = _ingreso(as_admin)
    r = as_admin.post(f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "derivado"})
    assert r.status_code == 200
    assert r.json()["motivo_cierre"] is None


def test_post_cierre_no_cierra_otra_vez_un_caso_cerrado(as_admin):
    ing = _ingreso(as_admin)
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    r = as_admin.post(
        f"/api/v1/ingresos/{ing['id']}/cierre",
        json={"estado": "cerrado", "motivo_cierre": "alta_medica"},
    )
    assert r.status_code == 409
    # tampoco se puede "derivar" un caso cerrado: sería reabrirlo sin perfil
    r = as_admin.post(f"/api/v1/ingresos/{ing['id']}/cierre", json={"estado": "derivado"})
    assert r.status_code == 409


# ── Dashboard ──────────────────────────────────────────────────────────────────
def test_cerrado_deja_de_contar_como_activo(as_admin, db_session):
    ing = _ingreso(as_admin)
    antes = as_admin.get("/api/v1/dashboard/activos").json()["total"]
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    assert as_admin.get("/api/v1/dashboard/activos").json()["total"] == antes - 1


# ── Alertas ────────────────────────────────────────────────────────────────────
def _licencia(db, ingreso_id, hoy):
    lm = LicenciaMedica(
        ingreso_id=ingreso_id,
        tipo_lm="1",
        tipo_reposo="total",
        fecha_inicio=hoy,
        fecha_termino=hoy,
        fecha_emision=hoy,
        inicio_reposo=hoy,
        fin_reposo=hoy,
        cantidad_dias=2,
        diagnostico="F32",
        anulada=False,
    )
    db.add(lm)
    db.flush()
    return lm


def _consentimiento_pendiente(db, ingreso_id):
    c = db.scalar(select(Consentimiento).where(Consentimiento.ingreso_id == ingreso_id))
    if c is None:
        db.add(Consentimiento(ingreso_id=ingreso_id, estado="pendiente"))
    else:
        c.estado = "pendiente"
    db.flush()


def _alerta_abierta(db, tipo, caso_tipo, caso_id):
    a = AlertaNotif(
        tipo=tipo,
        estado=EstadoAlerta.PENDIENTE.value,
        caso_id=caso_id,
        caso_tipo=caso_tipo,
        usuario_id=None,
        plazo_objetivo=datetime.combine(date.today(), time.min, tzinfo=timezone.utc),
        ventana_dias=0,
        email_enviado=False,
    )
    db.add(a)
    db.flush()
    return a


def test_cerrar_resuelve_alertas_abiertas_del_ingreso(as_admin, db_session):
    ing = _ingreso(as_admin)
    otro = _ingreso(as_admin, rut="22.222.222-2", nombre="Otra Persona")
    lic = _licencia(db_session, ing["id"], date.today())
    a_ingreso = _alerta_abierta(db_session, TipoAlerta.CONSENTIMIENTO_PENDIENTE.value, "ingreso", ing["id"])
    a_lic = _alerta_abierta(db_session, TipoAlerta.VENCIMIENTO_LICENCIA.value, "licencia", lic.id)
    a_otro = _alerta_abierta(db_session, TipoAlerta.CONSENTIMIENTO_PENDIENTE.value, "ingreso", otro["id"])

    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="alta_medica")

    db_session.refresh(a_ingreso)
    db_session.refresh(a_lic)
    db_session.refresh(a_otro)
    assert a_ingreso.estado == EstadoAlerta.RESUELTA.value
    assert a_ingreso.resuelta_en is not None
    assert a_lic.estado == EstadoAlerta.RESUELTA.value
    assert a_otro.estado == EstadoAlerta.PENDIENTE.value


def test_job_no_genera_alertas_de_un_caso_cerrado(as_admin, db_session):
    activo = _ingreso(as_admin, rut="33.333.333-3", nombre="Caso Activo")
    cerrado = _ingreso(as_admin)
    hoy = date.today()
    _licencia(db_session, activo["id"], hoy)
    _licencia(db_session, cerrado["id"], hoy)
    for ing in (activo, cerrado):
        _consentimiento_pendiente(db_session, ing["id"])
    _patch(as_admin, cerrado["id"], estado="cerrado", motivo_cierre="abandono")

    ejecutar_job_alertas(db_session, hoy=hoy)

    licencias = {
        lm.id: lm.ingreso_id for lm in db_session.scalars(select(LicenciaMedica))
    }
    generadas = list(db_session.scalars(select(AlertaNotif)))
    for a in generadas:
        if a.caso_tipo == "ingreso":
            assert a.caso_id != cerrado["id"]
        if a.caso_tipo == "licencia":
            assert licencias[a.caso_id] != cerrado["id"]
    assert any(a.caso_tipo == "ingreso" and a.caso_id == activo["id"] for a in generadas)
    assert any(a.caso_tipo == "licencia" and licencias[a.caso_id] == activo["id"] for a in generadas)


def test_al_reabrir_el_job_vuelve_a_alertar(as_admin, as_coordinacion, db_session):
    ing = _ingreso(as_admin)
    _consentimiento_pendiente(db_session, ing["id"])
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    ejecutar_job_alertas(db_session)
    assert not list(db_session.scalars(select(AlertaNotif).where(AlertaNotif.caso_id == ing["id"], AlertaNotif.caso_tipo == "ingreso")))
    _patch(as_coordinacion, ing["id"], estado="activo")
    ejecutar_job_alertas(db_session)
    assert list(db_session.scalars(select(AlertaNotif).where(AlertaNotif.caso_id == ing["id"], AlertaNotif.caso_tipo == "ingreso")))


def test_ingreso_cerrado_helper(as_admin, db_session):
    from app.services.alertas_cierre import ingreso_cerrado

    ing = _ingreso(as_admin)
    assert ingreso_cerrado(db_session, ing["id"]) is False
    _patch(as_admin, ing["id"], estado="cerrado", motivo_cierre="abandono")
    assert ingreso_cerrado(db_session, ing["id"]) is True
    assert db_session.get(Ingreso, ing["id"]).motivo_cierre == "abandono"
