"""Destinatario de las alertas: ``Ingreso.profesional_id`` no es un usuario.

``profesional_id`` apunta al catálogo de profesionales (``profesional.id``), no a
``usuario``. Usarlo como ``alerta_notif.usuario_id`` asignaba la alerta a quien tuviera
ese mismo id de usuario —otra persona— y la sacaba del panel general. Hasta que el CEPA
defina quién recibe cada alerta (P8 del diseño 2026-10-16-cita-desde-salutem), todas
quedan sin destinatario y van al panel general.
"""

import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.models.alertas import AlertaNotif
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.services.alertas import _resolver_usuario, ejecutar_job_alertas
from app.services.alertas_citas import alertar_inasistencia
from app.services.config_alertas import cargar_ventanas
from app.services.salutem_sync.alertas_control import alertar_atencion

HOY = date.today()


def _otro_usuario(db: Session) -> Usuario:
    u = Usuario(username="otra_persona", nombre="Otra Persona", hashed_password="x",
                rol="Administrativo", activo=True, intentos_fallidos=0)
    db.add(u)
    db.flush()
    return u


def _ingreso_con_profesional(db: Session, profesional_id: int, rut: str = "10000091") -> Ingreso:
    """Ingreso cuyo profesional_id coincide con el id de un usuario que no es su profesional."""
    p = Paciente(rut=rut, nombre="Paciente Destinatario", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    i = Ingreso(
        paciente_id=p.id, folio=f"F-DEST-{rut}", folio_manual=True, fecha_ingreso=date(2026, 1, 1),
        tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="test", estado="activo", profesional_id=profesional_id,
    )
    db.add(i)
    db.flush()
    return i


def test_resolver_usuario_no_usa_el_profesional_del_ingreso(db_session: Session):
    otro = _otro_usuario(db_session)
    ingreso = _ingreso_con_profesional(db_session, otro.id)
    assert _resolver_usuario(ingreso.id, db_session) is None
    assert _resolver_usuario(None, db_session) is None


def test_job_diario_deja_la_alerta_sin_destinatario(db_session: Session):
    otro = _otro_usuario(db_session)
    ingreso = _ingreso_con_profesional(db_session, otro.id)
    oda = Oda(ingreso_id=ingreso.id, identificador="ODA-DEST-1",
              fecha_vencimiento=HOY + timedelta(days=3), vigente=True)
    db_session.add(oda)
    db_session.flush()

    ejecutar_job_alertas(db_session, actor="test")

    (alerta,) = db_session.scalars(
        select(AlertaNotif).where(AlertaNotif.tipo == TipoAlerta.ODA_POR_VENCER.value,
                                  AlertaNotif.caso_id == oda.id)
    ).all()
    assert alerta.usuario_id is None


def test_inasistencia_queda_sin_destinatario(db_session: Session):
    otro = _otro_usuario(db_session)
    ingreso = _ingreso_con_profesional(db_session, otro.id)
    cita = Cita(ingreso_id=ingreso.id, estado="inasistencia", fecha=HOY - timedelta(days=1),
                salutem_cita_id=930001, origen="SALUTEM", especialidad="Médico/a")
    db_session.add(cita)
    db_session.flush()

    assert alertar_inasistencia(db_session, salutem_cita_id=930001, cita=cita, hoy=HOY,
                                ventanas=cargar_ventanas(db_session)) is True

    (alerta,) = db_session.scalars(
        select(AlertaNotif).where(AlertaNotif.tipo == TipoAlerta.INASISTENCIA.value)
    ).all()
    assert alerta.usuario_id is None


def test_alertas_de_atencion_salutem_quedan_sin_destinatario(db_session: Session):
    otro = _otro_usuario(db_session)
    ingreso = _ingreso_con_profesional(db_session, otro.id)

    creadas = alertar_atencion(db_session, 940001, ingreso.id, HOY, True, {}, HOY)

    assert creadas == 1
    (alerta,) = db_session.scalars(
        select(AlertaNotif).where(AlertaNotif.caso_id == 940001)
    ).all()
    assert alerta.usuario_id is None


def test_administrativo_ve_en_el_panel_la_alerta_de_un_ingreso_con_profesional(
    as_admin: TestClient, db_session: Session
):
    otro = _otro_usuario(db_session)
    ingreso = _ingreso_con_profesional(db_session, otro.id)
    oda = Oda(ingreso_id=ingreso.id, identificador="ODA-DEST-2",
              fecha_vencimiento=HOY + timedelta(days=3), vigente=True)
    db_session.add(oda)
    db_session.flush()
    ejecutar_job_alertas(db_session, actor="test")

    r = as_admin.get("/api/v1/alertas")

    assert r.status_code == 200
    assert any(a["caso_id"] == oda.id and a["tipo"] == TipoAlerta.ODA_POR_VENCER.value
               for a in r.json())


# ── Migración 1365: saneamiento de las alertas abiertas mal asignadas ─────────────────


def _migracion_1365():
    ruta = (Path(__file__).resolve().parents[1] / "migrations" / "versions"
            / "1365_alerta_notif_sin_profesional.py")
    spec = importlib.util.spec_from_file_location("mig_1365", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _alerta(db: Session, estado: str, usuario_id: int | None, caso_id: int) -> AlertaNotif:
    a = AlertaNotif(
        tipo=TipoAlerta.ODA_POR_VENCER.value, estado=estado, caso_id=caso_id, caso_tipo="oda",
        usuario_id=usuario_id, plazo_objetivo=datetime(2026, 10, 20, tzinfo=timezone.utc),
        ventana_dias=7, email_enviado=False,
    )
    db.add(a)
    db.flush()
    return a


def test_migracion_libera_las_alertas_abiertas_y_conserva_las_resueltas(db_session: Session):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    pendiente = _alerta(db_session, EstadoAlerta.PENDIENTE.value, 7, 950001)
    leida = _alerta(db_session, EstadoAlerta.LEIDA.value, 7, 950002)
    resuelta = _alerta(db_session, EstadoAlerta.RESUELTA.value, 7, 950003)
    sin_destinatario = _alerta(db_session, EstadoAlerta.PENDIENTE.value, None, 950004)

    mig = _migracion_1365()
    ctx = MigrationContext.configure(db_session.connection())
    with Operations.context(ctx):
        mig._liberar_alertas_abiertas()

    for a in (pendiente, leida, resuelta, sin_destinatario):
        db_session.refresh(a)
    assert pendiente.usuario_id is None
    assert leida.usuario_id is None
    assert resuelta.usuario_id == 7
    assert sin_destinatario.usuario_id is None
