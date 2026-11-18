"""Alerta «RECA por solicitar» (QA-003, 18-11-2026): reglas, idempotencia y resolución."""

import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import oracle

from app.models.alertas import AlertaNotif
from app.models.config_alerta import ConfigAlerta
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro, Reca
from app.services.alertas import ejecutar_job_alertas
from app.services.alertas_cierre import resolver_alertas_de_ingreso
from app.services.alertas_reca import CASO_TIPO, TIPO, alertar_reca_por_solicitar
from app.services.reintegro import registrar_solicitud_reca

FECHA_CASO = datetime.date(2026, 11, 2)
DIA_5 = FECHA_CASO + datetime.timedelta(days=5)


def _caso(db, *, estado="activo", fecha_caso=FECHA_CASO, estado_reintegro="pendiente", n=1) -> CasoReintegro:
    paciente = Paciente(rut=f"1234567{n}5", nombre=f"Paciente {n}", sexo="F", edad=40, region="Maule")
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(
        paciente_id=paciente.id, folio=f"F-2026-R{n:03d}", folio_manual=True, fecha_ingreso=fecha_caso,
        tipo_derivacion="DIAT", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="prueba", estado=estado,
    )
    db.add(ingreso)
    db.flush()
    caso = CasoReintegro(
        ingreso_id=ingreso.id, nombre=paciente.nombre, tipo_derivacion="DIAT", fecha_caso=fecha_caso,
        region="Maule", estado_reintegro=estado_reintegro,
    )
    db.add(caso)
    db.flush()
    return caso


def _reca(db, caso: CasoReintegro) -> None:
    db.add(Reca(caso_reintegro_id=caso.id, fecha_reca=FECHA_CASO, tipo_reca="AT", numero_reca="R-1", razon_social="X"))
    db.flush()
    db.refresh(caso)


def _config(db, **cambios) -> None:
    """La migración ya siembra la fila: se edita, como lo haría Coordinación."""
    fila = db.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == TIPO))
    for campo, valor in cambios.items():
        setattr(fila, campo, valor)
    db.flush()


def _alertas(db) -> list[AlertaNotif]:
    return list(db.scalars(select(AlertaNotif).where(AlertaNotif.tipo == TIPO).order_by(AlertaNotif.id)))


def test_alerta_a_los_5_dias_corridos_y_no_antes(db_session):
    caso = _caso(db_session)

    ejecutar_job_alertas(db_session, hoy=DIA_5 - datetime.timedelta(days=1))
    assert _alertas(db_session) == []

    assert ejecutar_job_alertas(db_session, hoy=DIA_5) == 1
    [a] = _alertas(db_session)
    assert (a.caso_tipo, a.caso_id, a.estado, a.ventana_dias) == (CASO_TIPO, caso.id, "pendiente", 5)
    assert a.plazo_objetivo.astimezone(datetime.timezone.utc).date() == DIA_5
    assert a.usuario_id is None


def test_los_dias_son_corridos_no_habiles(db_session):
    # 2026-11-02 es lunes: 5 días corridos = sábado 7; en hábiles sería el lunes 9.
    _caso(db_session)

    ejecutar_job_alertas(db_session, hoy=datetime.date(2026, 11, 7))

    assert len(_alertas(db_session)) == 1


def test_es_idempotente(db_session):
    _caso(db_session)

    ejecutar_job_alertas(db_session, hoy=DIA_5)
    assert ejecutar_job_alertas(db_session, hoy=DIA_5 + datetime.timedelta(days=3)) == 0

    assert len(_alertas(db_session)) == 1


def test_el_plazo_se_edita_en_la_configuracion(db_session):
    _caso(db_session)
    _config(db_session, dias=10)

    ejecutar_job_alertas(db_session, hoy=DIA_5)
    assert _alertas(db_session) == []

    ejecutar_job_alertas(db_session, hoy=FECHA_CASO + datetime.timedelta(days=10))
    [a] = _alertas(db_session)
    assert a.ventana_dias == 10


def test_tipo_apagado_no_alerta(db_session):
    _caso(db_session)
    _config(db_session, activo=False)

    ejecutar_job_alertas(db_session, hoy=DIA_5)

    assert _alertas(db_session) == []


@pytest.mark.parametrize(
    "preparar",
    [
        pytest.param(lambda db, c: setattr(c, "fecha_solicitud_reca", FECHA_CASO), id="con_solicitud"),
        pytest.param(lambda db, c: _reca(db, c), id="con_reca"),
        pytest.param(lambda db, c: setattr(c, "estado_reintegro", "total"), id="reintegro_total"),
        pytest.param(lambda db, c: setattr(db.get(Ingreso, c.ingreso_id), "estado", "cerrado"), id="ingreso_cerrado"),
    ],
)
def test_casos_que_no_alertan(db_session, preparar):
    caso = _caso(db_session)
    preparar(db_session, caso)
    db_session.flush()

    ejecutar_job_alertas(db_session, hoy=DIA_5 + datetime.timedelta(days=30))

    assert _alertas(db_session) == []


def test_reintegro_parcial_si_alerta(db_session):
    _caso(db_session, estado_reintegro="parcial")

    ejecutar_job_alertas(db_session, hoy=DIA_5)

    assert len(_alertas(db_session)) == 1


def test_solo_alerta_los_casos_que_corresponden(db_session):
    _caso(db_session, n=1)
    _caso(db_session, n=2, fecha_caso=datetime.date(2026, 11, 6))  # aún no cumple

    ejecutar_job_alertas(db_session, hoy=DIA_5)

    assert len(_alertas(db_session)) == 1


def test_registrar_la_solicitud_resuelve_la_alerta(db_session):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)

    registrar_solicitud_reca(db_session, caso, datetime.date(2026, 11, 4), hoy=DIA_5)

    [a] = _alertas(db_session)
    assert a.estado == "resuelta" and a.resuelta_en is not None
    assert ejecutar_job_alertas(db_session, hoy=DIA_5) == 0  # y no reaparece


def test_registrar_la_reca_resuelve_la_alerta(db_session, as_admin):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)

    r = as_admin.post(
        f"/api/v1/reintegros/{caso.id}/reca",
        json={"fecha_reca": "2026-11-06", "tipo_reca": "AT", "numero_reca": "A-1",
              "razon_social": "Empresa SA", "solicita_medidas": False},
    )

    assert r.status_code == 201
    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]


def test_el_reintegro_total_resuelve_la_alerta(db_session, as_admin):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)

    r = as_admin.patch(
        f"/api/v1/reintegros/{caso.id}/cierre",
        json={"estado_reintegro": "total", "fecha_reintegro": "2026-11-20", "remitido_isl": False,
              "alta_medica": True, "fecha_alta_medica": "2026-11-19", "alta_psicologica": False},
    )

    assert r.status_code == 200, r.text
    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]


def test_el_job_resuelve_si_el_caso_dejo_de_aplicar_sin_pasar_por_el_servicio(db_session):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)
    caso.estado_reintegro = "total"
    db_session.flush()

    ejecutar_job_alertas(db_session, hoy=DIA_5)

    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]


def test_al_cerrarse_el_ingreso_se_resuelve(db_session):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)

    assert resolver_alertas_de_ingreso(db_session, caso.ingreso_id) >= 1

    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]


def test_el_job_resuelve_las_del_ingreso_cerrado(db_session):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)
    db_session.get(Ingreso, caso.ingreso_id).estado = "cerrado"
    db_session.flush()

    ejecutar_job_alertas(db_session, hoy=DIA_5)

    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]


def test_una_alerta_resuelta_a_mano_no_reaparece(db_session):
    _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)
    [a] = _alertas(db_session)
    a.estado = "resuelta"
    db_session.flush()

    assert ejecutar_job_alertas(db_session, hoy=DIA_5 + datetime.timedelta(days=1)) == 0

    assert len(_alertas(db_session)) == 1


def test_el_listado_trae_el_paciente_del_caso(db_session, as_coordinacion):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)
    paciente_id = db_session.get(Ingreso, caso.ingreso_id).paciente_id

    [fila] = [a for a in as_coordinacion.get("/api/v1/alertas").json() if a["tipo"] == TIPO]

    assert (fila["caso_tipo"], fila["caso_id"], fila["paciente_id"]) == (CASO_TIPO, caso.id, paciente_id)
    assert fila["paciente_nombre"] == "Paciente 1"


def test_la_auditoria_registra_la_generacion(db_session):
    from app.models.audit_log import AuditLog

    _caso(db_session)

    ejecutar_job_alertas(db_session, hoy=DIA_5)

    ids = set(db_session.scalars(select(AuditLog.entity_id).where(AuditLog.entity == "alerta_notif")))
    assert "reca:1" in ids


def test_la_configuracion_la_expone(as_coordinacion):
    filas = {c["tipo"]: c for c in as_coordinacion.get("/api/v1/config-alertas").json()}
    assert (filas[TIPO]["dias"], filas[TIPO]["habiles"], filas[TIPO]["activo"]) == (5, False, True)
    assert filas["proyeccion_reintegro"]["activo"] is True


def test_las_consultas_compilan_en_oracle(db_session):
    """No hay Oracle local: se compilan las consultas nuevas con su dialecto."""
    from app.services import alertas_reca

    consultas = [
        select(CasoReintegro.id, CasoReintegro.fecha_caso, CasoReintegro.ingreso_id)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(CasoReintegro.fecha_caso <= DIA_5, ~alertas_reca._no_requiere_solicitud()),
        select(AlertaNotif)
        .join(CasoReintegro, CasoReintegro.id == AlertaNotif.caso_id)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(AlertaNotif.estado.in_(alertas_reca._ABIERTAS), alertas_reca._no_requiere_solicitud()),
    ]
    for consulta in consultas:
        sql = str(consulta.compile(dialect=oracle.dialect()))
        assert "IS TRUE" not in sql.upper() and "IS FALSE" not in sql.upper()
    # y la función completa corre sin errores
    assert alertar_reca_por_solicitar(db_session, DIA_5, {}, "test") == (0, 0)


def test_el_contexto_de_la_alerta_abre_el_caso(db_session, as_coordinacion):
    caso = _caso(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_5)
    [a] = _alertas(db_session)

    r = as_coordinacion.get(f"/api/v1/alertas/{a.id}/contexto")

    assert r.status_code == 200
    assert (r.json()["ingreso_id"], r.json()["paciente_nombre"]) == (caso.ingreso_id, "Paciente 1")
