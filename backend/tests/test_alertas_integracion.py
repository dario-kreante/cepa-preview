"""Tests de integración EPIC-10 rework — CEPA-100..102.

Cubre:
- DD-A: un test de integración por tipo de hito (constructor ORM real).
- DD-B: auditoría antes del commit en job, PATCH alerta y tareas.
- DD-C: email en usuario; omisión segura sin SMTP / sin email.
- DD-D: idempotencia por (caso, tipo, plazo_objetivo) — re-ejecución no duplica.
- DD-E: transiciones de estado válidas e inválidas.
"""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alertas import AlertaNotif
from app.models.audit_log import AuditLog
from app.models.consentimiento import Consentimiento
from app.models.control_medico import ControlMedico
from app.models.ept import CasoEpt, PlazoEpt
from app.models.farmacos import Receta, RegistroFarmacologico
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.services.alertas import ejecutar_job_alertas


# ---------------------------------------------------------------------------
# Helpers de fixtures de dominio
# ---------------------------------------------------------------------------


def _make_ingreso(db: Session, *, folio: str = "F-INT-001") -> Ingreso:
    paciente = Paciente(rut="99999999K", nombre="Test Paciente", sexo="M", edad=30, region="Maule")
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio=folio,
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 1),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Test",
        estado="activo",
    )
    db.add(ingreso)
    db.flush()
    return ingreso


def _today_plus(days: int) -> datetime.date:
    return datetime.date.today() + datetime.timedelta(days=days)


# ---------------------------------------------------------------------------
# DD-A: un test de integración por tipo de hito
# ---------------------------------------------------------------------------


def test_job_genera_alerta_oda_por_vencer(db_session: Session):
    """DD-A: ODA dentro de ventana (7 días) genera alerta_notif."""
    ingreso = _make_ingreso(db_session, folio="F-ODA-001")
    oda = Oda(
        ingreso_id=ingreso.id,
        identificador="ODA-TEST-001",
        fecha_vencimiento=_today_plus(3),  # dentro de ventana de 7 días
        vigente=True,
    )
    db_session.add(oda)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    alerta = db_session.scalars(
        __import__("sqlalchemy", fromlist=["select"]).select(AlertaNotif).where(
            AlertaNotif.tipo == "oda_por_vencer",
            AlertaNotif.caso_id == oda.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.estado == "pendiente"
    assert alerta.caso_tipo == "oda"


def test_job_genera_alerta_vencimiento_licencia(db_session: Session):
    """DD-A: LicenciaMedica no anulada con fin_reposo dentro de ventana → alerta."""
    ingreso = _make_ingreso(db_session, folio="F-LM-001")
    lm = LicenciaMedica(
        ingreso_id=ingreso.id,
        tipo_lm="1",
        tipo_reposo="total",
        fecha_inicio=datetime.date.today(),
        fecha_termino=_today_plus(2),
        fecha_emision=datetime.date.today(),
        inicio_reposo=datetime.date.today(),
        fin_reposo=_today_plus(2),  # dentro de ventana de 3 días hábiles
        cantidad_dias=2,
        diagnostico="F32",
        anulada=False,
    )
    db_session.add(lm)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    alerta = db_session.scalars(
        __import__("sqlalchemy", fromlist=["select"]).select(AlertaNotif).where(
            AlertaNotif.tipo == "vencimiento_licencia",
            AlertaNotif.caso_id == lm.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.caso_tipo == "licencia"


def test_job_genera_alerta_plazo_ept(db_session: Session):
    """DD-A: PlazoEpt con plazo_informe_ept dentro de ventana → alerta plazo_ept."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-EPT-001")
    caso_ept = CasoEpt(
        ingreso_id=ingreso.id,
        mes="2026-06",
        fecha_ingreso_ept=datetime.date(2026, 1, 1),
        nombre_trabajador="Pedro Test",
        rut_trabajador="11111111-1",
        region_trabajador="Maule",
        eista="EISTA",
        factor_riesgo="ruido",
        corresponde_ept=True,
    )
    db_session.add(caso_ept)
    db_session.flush()

    plazo_ept = PlazoEpt(
        caso_ept_id=caso_ept.id,
        plazo_informe_ept=_today_plus(3),  # dentro de ventana 5 días hábiles
        plazo_portal_isl=None,
    )
    db_session.add(plazo_ept)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    alerta = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "plazo_ept",
            AlertaNotif.caso_id == plazo_ept.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.caso_tipo == "ept"


def test_job_genera_alerta_plazo_isl(db_session: Session):
    """DD-A: PlazoEpt con plazo_portal_isl dentro de ventana → alerta plazo_isl."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-ISL-001")
    caso_ept = CasoEpt(
        ingreso_id=ingreso.id,
        mes="2026-06",
        fecha_ingreso_ept=datetime.date(2026, 1, 1),
        nombre_trabajador="María ISL",
        rut_trabajador="22222222-2",
        region_trabajador="Maule",
        eista="EISTA2",
        factor_riesgo="carga",
        corresponde_ept=True,
    )
    db_session.add(caso_ept)
    db_session.flush()

    plazo_ept = PlazoEpt(
        caso_ept_id=caso_ept.id,
        plazo_informe_ept=None,
        plazo_portal_isl=_today_plus(3),  # dentro de ventana 5 días hábiles
    )
    db_session.add(plazo_ept)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    alerta = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "plazo_isl",
            AlertaNotif.caso_id == plazo_ept.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.caso_tipo == "ept"


def test_job_genera_alerta_consentimiento_pendiente(db_session: Session):
    """DD-A: Consentimiento no firmado → alerta consentimiento_pendiente."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-CON-001")
    consentimiento = Consentimiento(
        ingreso_id=ingreso.id,
        estado="pendiente",
    )
    db_session.add(consentimiento)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    alerta = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "consentimiento_pendiente",
            AlertaNotif.caso_id == ingreso.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.caso_tipo == "ingreso"


def test_job_genera_alerta_control_medico(db_session: Session):
    """DD-A: ControlMedico con proximo_control dentro de ventana y no agendado → alerta."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-CM-001")
    control = ControlMedico(
        ingreso_id=ingreso.id,
        fecha_control=datetime.date.today(),
        semana_control=1,
        medico_tratante="Dr. Test",
        region_derivacion="Maule",
        proximo_control=_today_plus(5),  # dentro de ventana 7 días
        proximo_agendado=False,
    )
    db_session.add(control)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    alerta = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "control_medico",
            AlertaNotif.caso_id == control.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.caso_tipo == "control_medico"  # F6: caso_tipo corregido


def test_job_genera_alerta_receta_por_renovar(db_session: Session):
    """DD-A: Receta con fecha_revision en ventana y sin fecha_envio → alerta receta_por_renovar."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-REC-001")
    reg = RegistroFarmacologico(
        ingreso_id=ingreso.id,
        medico_tratante="Dr. Fármaco",
        estado_farmacologico="activo",
        activo=True,
    )
    db_session.add(reg)
    db_session.flush()

    receta = Receta(
        registro_id=reg.id,
        fecha_emision=datetime.date.today(),
        fecha_revision=_today_plus(3),  # dentro de ventana 5 días
        fecha_envio=None,
        marca_medicamento="Sertralina",
    )
    db_session.add(receta)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    alerta = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "receta_por_renovar",
            AlertaNotif.caso_id == receta.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.caso_tipo == "receta"


# ---------------------------------------------------------------------------
# DD-D: idempotencia — re-ejecución no duplica alertas
# ---------------------------------------------------------------------------


def test_job_idempotente_no_duplica_en_segunda_ejecucion(db_session: Session):
    """DD-D: segunda ejecución del job no crea alertas duplicadas para el mismo plazo."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-IDMP-001")
    oda = Oda(
        ingreso_id=ingreso.id,
        identificador="ODA-IDMP",
        fecha_vencimiento=_today_plus(2),
        vigente=True,
    )
    db_session.add(oda)
    db_session.flush()

    ejecutar_job_alertas(db_session, actor="test")
    segunda = ejecutar_job_alertas(db_session, actor="test")

    # Segunda ejecución no debe generar nuevas alertas para el mismo plazo
    assert segunda == 0

    count = db_session.scalar(
        select(__import__("sqlalchemy", fromlist=["func"]).func.count()).select_from(AlertaNotif).where(
            AlertaNotif.tipo == "oda_por_vencer",
            AlertaNotif.caso_id == oda.id,
        )
    )
    assert count == 1


def test_job_genera_nueva_alerta_por_nuevo_plazo(db_session: Session):
    """DD-D / RN-4: un nuevo plazo en el mismo caso genera una alerta adicional.

    Simula la situación en que primero se crea una alerta para oda_v1
    (ya resuelta) y luego se crea oda_v2 con plazo_objetivo distinto.
    """
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-NPLAZO-001")

    oda_v1 = Oda(
        ingreso_id=ingreso.id,
        identificador="ODA-V1",
        fecha_vencimiento=_today_plus(2),
        vigente=False,  # ya no vigente: no genera hito
    )
    db_session.add(oda_v1)

    oda_v2 = Oda(
        ingreso_id=ingreso.id,
        identificador="ODA-V2",
        fecha_vencimiento=_today_plus(4),  # plazo distinto, vigente
        vigente=True,
    )
    db_session.add(oda_v2)
    db_session.flush()

    # Marcar manualmente alerta preexistente para oda_v1 (simula que ya existía)
    alerta_previa = AlertaNotif(
        tipo="oda_por_vencer",
        estado="resuelta",
        caso_id=oda_v1.id,
        caso_tipo="oda",
        usuario_id=None,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime(
            *_today_plus(2).timetuple()[:3],
            tzinfo=__import__("datetime", fromlist=["timezone"]).timezone.utc,
        ),
        ventana_dias=7,
        email_enviado=False,
    )
    db_session.add(alerta_previa)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1  # oda_v2 genera una alerta nueva

    alerta_v2 = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "oda_por_vencer",
            AlertaNotif.caso_id == oda_v2.id,
        )
    ).first()
    assert alerta_v2 is not None


# ---------------------------------------------------------------------------
# DD-B: auditoría antes del commit
# ---------------------------------------------------------------------------


def test_job_registra_auditoria_antes_de_commit(db_session: Session):
    """DD-B: ejecutar_job_alertas registra AuditLog ANTES del commit."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-AUD-001")
    oda = Oda(
        ingreso_id=ingreso.id,
        identificador="ODA-AUD",
        fecha_vencimiento=_today_plus(2),
        vigente=True,
    )
    db_session.add(oda)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test_actor")
    assert n >= 1

    log = db_session.scalars(
        select(AuditLog).where(
            AuditLog.actor == "test_actor",
            AuditLog.entity == "alerta_notif",
            AuditLog.action == "CREATE",
        )
    ).first()
    assert log is not None
    assert log.entity_id.startswith("job:")


def test_patch_alerta_registra_auditoria(as_admin: TestClient, db_session: Session):
    """DD-B: PATCH /alertas/{id} registra AuditLog antes del commit."""
    from sqlalchemy import select

    uid = as_admin.get("/whoami-test").json()["id"]
    alerta = AlertaNotif(
        tipo="oda_por_vencer",
        estado="pendiente",
        caso_id=888,
        caso_tipo="oda",
        usuario_id=uid,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        )
        + __import__("datetime", fromlist=["timedelta"]).timedelta(days=3),
        ventana_dias=7,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "leida"})
    assert resp.status_code == 200

    log = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "alerta_notif",
            AuditLog.entity_id == str(alerta.id),
            AuditLog.action == "UPDATE",
        )
    ).first()
    assert log is not None


def test_patch_tarea_registra_auditoria(as_admin: TestClient, db_session: Session):
    """DD-B: PATCH /tareas/{id} registra AuditLog antes del commit."""
    from sqlalchemy import select

    uid = as_admin.get("/whoami-test").json()["id"]

    resp_create = as_admin.post(
        "/api/v1/tareas",
        json={
            "titulo": "Tarea auditoría test",
            "descripcion": "Desc",
            "tipo_tarea": "revision",
            "usuario_id": uid,
        },
    )
    assert resp_create.status_code == 201
    tarea_id = resp_create.json()["id"]

    resp_patch = as_admin.patch(
        f"/api/v1/tareas/{tarea_id}", json={"estado": "en_progreso"}
    )
    assert resp_patch.status_code == 200

    log = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "tarea_item",
            AuditLog.entity_id == str(tarea_id),
            AuditLog.action == "UPDATE",
        )
    ).first()
    assert log is not None


# ---------------------------------------------------------------------------
# DD-C: email en usuario + envío con omisiones seguras
# ---------------------------------------------------------------------------


def test_enviar_correos_omite_sin_smtp(as_admin: TestClient):
    """DD-C: sin smtp_host → retorna inmediatamente enviados=0 sin marcar email_enviado."""
    resp = as_admin.post("/api/v1/alertas/enviar-correos")
    # Sin SMTP configurado → debe responder 200 con alertas_generadas=0
    assert resp.status_code == 200
    data = resp.json()
    assert data["alertas_generadas"] == 0


def test_enviar_correos_con_fake_sender_omite_usuario_sin_email(db_session: Session):
    """DD-C: alertas sin usuario o sin email → contadas como omitidas, no se envían."""
    from app.services.alertas import enviar_correos_alertas
    from app.services.email_sender import FakeEmailSender

    alerta = AlertaNotif(
        tipo="oda_por_vencer",
        estado="pendiente",
        caso_id=777,
        caso_tipo="oda",
        usuario_id=None,  # sin usuario
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=7,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    sender = FakeEmailSender()
    resultado = enviar_correos_alertas(db_session, sender=sender, actor="test")

    assert resultado["enviados"] == 0
    assert resultado["omitidas"] >= 1
    assert len(sender.enviados) == 0
    # email_enviado no se debe haber marcado
    db_session.refresh(alerta)
    assert alerta.email_enviado is False


def test_enviar_correos_con_usuario_con_email(db_session: Session):
    """DD-C: alerta con usuario con email → se envía y se marca email_enviado."""
    from app.auth.security import hash_password
    from app.services.alertas import enviar_correos_alertas
    from app.services.email_sender import FakeEmailSender

    usuario = Usuario(
        username="email_user_test",
        nombre="Email User",
        hashed_password=hash_password("Clave123!"),
        rol="Administrativo",
        activo=True,
        intentos_fallidos=0,
        email="test@example.com",
    )
    db_session.add(usuario)
    db_session.flush()

    alerta = AlertaNotif(
        tipo="oda_por_vencer",
        estado="pendiente",
        caso_id=555,
        caso_tipo="oda",
        usuario_id=usuario.id,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=7,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    sender = FakeEmailSender()
    resultado = enviar_correos_alertas(db_session, sender=sender, actor="test")

    assert resultado["enviados"] == 1
    assert len(sender.enviados) == 1
    assert sender.enviados[0]["to"] == "test@example.com"
    db_session.refresh(alerta)
    assert alerta.email_enviado is True


# ---------------------------------------------------------------------------
# DD-E: transiciones de estado
# ---------------------------------------------------------------------------


def test_transicion_pendiente_a_leida(as_admin: TestClient, db_session: Session):
    """DD-E: pendiente → leida es válida."""
    uid = as_admin.get("/whoami-test").json()["id"]
    alerta = AlertaNotif(
        tipo="oda_por_vencer",
        estado="pendiente",
        caso_id=100,
        caso_tipo="oda",
        usuario_id=uid,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=7,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "leida"})
    assert resp.status_code == 200
    assert resp.json()["estado"] == "leida"
    assert resp.json()["resuelta_en"] is None


def test_transicion_pendiente_a_resuelta(as_admin: TestClient, db_session: Session):
    """DD-E: pendiente → resuelta es válida y setea resuelta_en."""
    uid = as_admin.get("/whoami-test").json()["id"]
    alerta = AlertaNotif(
        tipo="control_medico",
        estado="pendiente",
        caso_id=101,
        caso_tipo="ingreso",
        usuario_id=uid,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=7,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "resuelta"})
    assert resp.status_code == 200
    assert resp.json()["estado"] == "resuelta"
    assert resp.json()["resuelta_en"] is not None


def test_transicion_leida_a_resuelta(as_admin: TestClient, db_session: Session):
    """DD-E: leida → resuelta es válida."""
    uid = as_admin.get("/whoami-test").json()["id"]
    alerta = AlertaNotif(
        tipo="plazo_ept",
        estado="leida",
        caso_id=102,
        caso_tipo="ept",
        usuario_id=uid,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=5,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "resuelta"})
    assert resp.status_code == 200
    assert resp.json()["estado"] == "resuelta"


def test_transicion_resuelta_a_pendiente_rechazada(as_admin: TestClient, db_session: Session):
    """DD-E: resuelta → pendiente está prohibida (422)."""
    uid = as_admin.get("/whoami-test").json()["id"]
    alerta = AlertaNotif(
        tipo="plazo_isl",
        estado="resuelta",
        caso_id=103,
        caso_tipo="ept",
        usuario_id=uid,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=5,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "pendiente"})
    assert resp.status_code == 422


def test_transicion_resuelta_a_leida_rechazada(as_admin: TestClient, db_session: Session):
    """DD-E: resuelta → leida está prohibida (422)."""
    uid = as_admin.get("/whoami-test").json()["id"]
    alerta = AlertaNotif(
        tipo="vencimiento_licencia",
        estado="resuelta",
        caso_id=104,
        caso_tipo="licencia",
        usuario_id=uid,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=3,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "leida"})
    assert resp.status_code == 422


def test_transicion_misma_estado_rechazada(as_admin: TestClient, db_session: Session):
    """DD-E: transición al mismo estado que el actual es rechazada (pendiente→pendiente)."""
    uid = as_admin.get("/whoami-test").json()["id"]
    alerta = AlertaNotif(
        tipo="consentimiento_pendiente",
        estado="pendiente",
        caso_id=105,
        caso_tipo="ingreso",
        usuario_id=uid,
        plazo_objetivo=__import__("datetime", fromlist=["datetime"]).datetime.now(
            __import__("datetime", fromlist=["timezone"]).timezone.utc
        ),
        ventana_dias=30,
        email_enviado=False,
    )
    db_session.add(alerta)
    db_session.flush()

    resp = as_admin.patch(f"/api/v1/alertas/{alerta.id}", json={"estado": "pendiente"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DD-C: usuario con email via API (crear y actualizar)
# ---------------------------------------------------------------------------


def test_crear_usuario_con_email(as_coordinacion: TestClient):
    """DD-C: UsuarioCreate acepta email opcional y lo persiste."""
    resp = as_coordinacion.post(
        "/api/v1/usuarios",
        json={
            "username": "usr_email_api",
            "nombre": "Usuario Email",
            "password": "Clave123!",
            "rol": "Administrativo",
            "email": "usr@example.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "usr@example.com"


def test_actualizar_usuario_email(as_coordinacion: TestClient):
    """DD-C: UsuarioUpdate permite cambiar el email."""
    # Crear primero
    resp_create = as_coordinacion.post(
        "/api/v1/usuarios",
        json={
            "username": "usr_update_email",
            "nombre": "Upd Email",
            "password": "Clave123!",
            "rol": "Coordinacion",
        },
    )
    assert resp_create.status_code == 201
    uid = resp_create.json()["id"]

    # Actualizar email
    resp_put = as_coordinacion.put(
        f"/api/v1/usuarios/{uid}",
        json={"email": "updated@example.com"},
    )
    assert resp_put.status_code == 200
    assert resp_put.json()["email"] == "updated@example.com"


# ---------------------------------------------------------------------------
# F5 — latest-per-ingreso en _construir_hitos_control_medico
# F6 — caso_tipo="control_medico"
# ---------------------------------------------------------------------------


def test_control_medico_solo_alerta_por_ultimo_control_por_ingreso(db_session: Session):
    """F5: si hay dos controles para el mismo ingreso, solo genera alerta para el más reciente."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-CM-LATEST-001")

    # control más antiguo — proximo_control en 2 días
    control_viejo = ControlMedico(
        ingreso_id=ingreso.id,
        fecha_control=datetime.date.today(),
        semana_control=1,
        medico_tratante="Dr. Viejo",
        region_derivacion="Maule",
        proximo_control=_today_plus(2),
        proximo_agendado=False,
    )
    db_session.add(control_viejo)
    db_session.flush()

    # control más reciente — proximo_control en 4 días (> 2)
    control_nuevo = ControlMedico(
        ingreso_id=ingreso.id,
        fecha_control=datetime.date.today(),
        semana_control=2,
        medico_tratante="Dr. Nuevo",
        region_derivacion="Maule",
        proximo_control=_today_plus(4),
        proximo_agendado=False,
    )
    db_session.add(control_nuevo)
    db_session.flush()

    n = ejecutar_job_alertas(db_session, actor="test")
    assert n >= 1

    # Solo debe existir alerta para el control más reciente (caso_id=control_nuevo.id)
    alerta_nuevo = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "control_medico",
            AlertaNotif.caso_id == control_nuevo.id,
        )
    ).first()
    assert alerta_nuevo is not None, "Se esperaba alerta para el control más reciente"

    # No debe existir alerta para el control viejo
    alerta_viejo = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "control_medico",
            AlertaNotif.caso_id == control_viejo.id,
        )
    ).first()
    assert alerta_viejo is None, "No debe generarse alerta para el control más antiguo del mismo ingreso"


def test_control_medico_caso_tipo_es_control_medico(db_session: Session):
    """F6: la alerta de control médico tiene caso_tipo='control_medico', no 'ingreso'."""
    from sqlalchemy import select

    ingreso = _make_ingreso(db_session, folio="F-CM-TIPO-001")
    control = ControlMedico(
        ingreso_id=ingreso.id,
        fecha_control=datetime.date.today(),
        semana_control=1,
        medico_tratante="Dr. Tipo",
        region_derivacion="Maule",
        proximo_control=_today_plus(3),
        proximo_agendado=False,
    )
    db_session.add(control)
    db_session.flush()

    ejecutar_job_alertas(db_session, actor="test")

    alerta = db_session.scalars(
        select(AlertaNotif).where(
            AlertaNotif.tipo == "control_medico",
            AlertaNotif.caso_id == control.id,
        )
    ).first()
    assert alerta is not None
    assert alerta.caso_tipo == "control_medico", (
        f"Se esperaba caso_tipo='control_medico', se obtuvo '{alerta.caso_tipo}'"
    )
