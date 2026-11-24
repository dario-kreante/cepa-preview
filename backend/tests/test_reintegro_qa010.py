"""QA-010 (QA 23-11-2026): reintegro.

- Opciones de la proyección de SALUTEM y su plazo estimado.
- Alerta «Pendiente de remitir a ISL» y marcar «Remitido a ISL» sin cerrar el caso.
- Ocupación del caso y precarga del alta (caso anterior del paciente, ficha de SALUTEM).
- Lista global de la pestaña Reintegro (casos activos y pendientes por registrar).
"""

import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import oracle

from app.domain.proyeccion_reintegro import (
    opcion_alertable,
    opcion_proyeccion,
    plazo_estimado,
    texto_alerta,
)
from app.models.alertas import AlertaNotif
from app.models.config_alerta import ConfigAlerta
from app.models.control_medico import ControlMedico
from app.models.ept import CasoEpt
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro, Reca
from app.models.salutem_copia import SalutemPersona
from app.services.alertas import ejecutar_job_alertas
from app.services.alertas_remitir_isl import TIPO, _no_requiere_remision
from app.services.reintegro_panel import ocupacion_de_contenido

FECHA_CASO = datetime.date(2026, 11, 2)
DIA_7 = FECHA_CASO + datetime.timedelta(days=7)
AHORA = datetime.datetime(2026, 11, 20, 12, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture(autouse=True)
def _sin_alerta_de_reca(db_session):
    """Se apaga «RECA por solicitar» para contar solo las alertas de este módulo."""
    db_session.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == "reca_por_solicitar")).activo = False
    db_session.flush()


def _paciente(db, n=1, **extra) -> Paciente:
    paciente = Paciente(rut=f"1111111{n}1", nombre=f"Paciente {n}", sexo="F", edad=40, region="Maule", **extra)
    db.add(paciente)
    db.flush()
    return paciente


def _ingreso(db, paciente: Paciente, *, tipo_derivacion="DIAT", estado="activo", n=1) -> Ingreso:
    ingreso = Ingreso(
        paciente_id=paciente.id, folio=f"F-2026-Q{paciente.id:03d}{n}", folio_manual=True,
        fecha_ingreso=FECHA_CASO, tipo_derivacion=tipo_derivacion, tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="prueba", estado=estado,
    )
    db.add(ingreso)
    db.flush()
    return ingreso


def _caso(db, ingreso: Ingreso, **extra) -> CasoReintegro:
    datos = dict(
        ingreso_id=ingreso.id, nombre="Paciente", tipo_derivacion=ingreso.tipo_derivacion,
        fecha_caso=FECHA_CASO, region="Maule",
    )
    datos.update(extra)
    caso = CasoReintegro(**datos)
    db.add(caso)
    db.flush()
    return caso


def _caso_isl(db, n=1, **extra) -> CasoReintegro:
    return _caso(db, _ingreso(db, _paciente(db, n)), **extra)


def _control(db, ingreso: Ingreso, fecha: datetime.date, proyeccion: str | None) -> ControlMedico:
    control = ControlMedico(
        ingreso_id=ingreso.id, fecha_control=fecha, semana_control=1, medico_tratante="Dra. X",
        region_derivacion="Maule", proyeccion_reintegro=proyeccion,
    )
    db.add(control)
    db.flush()
    return control


def _alerta_proyeccion(db, control: ControlMedico, estado="pendiente") -> AlertaNotif:
    alerta = AlertaNotif(
        tipo="proyeccion_reintegro", estado=estado, caso_id=control.id, caso_tipo="control_medico",
        plazo_objetivo=datetime.datetime.combine(control.fecha_control, datetime.time.min, tzinfo=datetime.timezone.utc),
        ventana_dias=1, email_enviado=False,
    )
    db.add(alerta)
    db.flush()
    return alerta


def _alertas(db) -> list[AlertaNotif]:
    return list(db.scalars(select(AlertaNotif).where(AlertaNotif.tipo == TIPO).order_by(AlertaNotif.id)))


# ── Opciones de la proyección ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("valor", "dias"),
    [
        ("1 semana aproximadamente", 7),
        ("2 semanas aproximadamente", 14),
        ("3 semanas aproximadamente", 21),
        ("Paciente con reintegro parcial", None),
    ],
)
def test_las_opciones_vigiladas_y_su_plazo(valor, dias):
    opcion = opcion_alertable(valor)
    assert opcion is not None and opcion.dias == dias
    esperado = None if dias is None else FECHA_CASO + datetime.timedelta(days=dias)
    assert plazo_estimado(opcion, FECHA_CASO) == esperado


@pytest.mark.parametrize(
    "valor", ["1 mes aproximadamente", "Más de 1 mes", "Paciente con reintegro total", "otra cosa", "", None]
)
def test_las_demas_no_alertan(valor):
    assert opcion_alertable(valor) is None


def test_la_comparacion_ignora_tildes_mayusculas_y_espacios():
    assert opcion_proyeccion("  MAS   de 1 MES. ").texto == "Más de 1 mes"
    assert opcion_alertable("1 SEMANA aproximadamente").texto == "1 semana aproximadamente"


def test_el_texto_de_la_alerta():
    assert texto_alerta(opcion_alertable("1 semana aproximadamente"), FECHA_CASO) == (
        "1 semana aproximadamente · reintegro estimado al 09-11-2026"
    )
    assert texto_alerta(opcion_alertable("paciente con reintegro parcial"), FECHA_CASO) == (
        "Paciente con reintegro parcial · seguimiento del reintegro"
    )


# ── Alerta «Pendiente de remitir a ISL» ─────────────────────────────────────


def test_alerta_a_los_7_dias_sin_remitir_y_no_antes(db_session):
    caso = _caso_isl(db_session)

    assert ejecutar_job_alertas(db_session, hoy=DIA_7 - datetime.timedelta(days=1)) == 0
    assert ejecutar_job_alertas(db_session, hoy=DIA_7) == 1

    [a] = _alertas(db_session)
    assert (a.caso_tipo, a.caso_id, a.estado, a.ventana_dias) == ("caso_reintegro", caso.id, "pendiente", 7)
    assert a.plazo_objetivo.astimezone(datetime.timezone.utc).date() == DIA_7


def test_es_idempotente(db_session):
    _caso_isl(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_7)

    assert ejecutar_job_alertas(db_session, hoy=DIA_7 + datetime.timedelta(days=3)) == 0
    assert len(_alertas(db_session)) == 1


def test_el_plazo_y_el_encendido_se_editan_en_la_configuracion(db_session):
    _caso_isl(db_session)
    fila = db_session.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == TIPO))
    fila.dias = 10
    db_session.flush()

    ejecutar_job_alertas(db_session, hoy=DIA_7)
    assert _alertas(db_session) == []

    fila.activo = False
    db_session.flush()
    ejecutar_job_alertas(db_session, hoy=FECHA_CASO + datetime.timedelta(days=10))
    assert _alertas(db_session) == []


def test_un_paciente_clinico_no_alerta(db_session):
    _caso(db_session, _ingreso(db_session, _paciente(db_session), tipo_derivacion="Particular"))

    ejecutar_job_alertas(db_session, hoy=DIA_7 + datetime.timedelta(days=5))

    assert _alertas(db_session) == []


@pytest.mark.parametrize(
    "preparar",
    [
        pytest.param(lambda db, c: setattr(c, "remitido_isl", True), id="remitido"),
        pytest.param(lambda db, c: setattr(c, "estado_reintegro", "total"), id="reintegro_total"),
        pytest.param(lambda db, c: setattr(db.get(Ingreso, c.ingreso_id), "estado", "cerrado"), id="ingreso_cerrado"),
        pytest.param(lambda db, c: setattr(c, "fecha_caso", FECHA_CASO - datetime.timedelta(days=61)), id="antiguo"),
    ],
)
def test_casos_que_no_alertan(db_session, preparar):
    caso = _caso_isl(db_session)
    preparar(db_session, caso)
    db_session.flush()

    ejecutar_job_alertas(db_session, hoy=DIA_7)

    assert _alertas(db_session) == []


def test_marcar_remitido_sin_cerrar_resuelve_la_alerta(db_session, as_admin):
    caso = _caso_isl(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_7)

    r = as_admin.patch(f"/api/v1/reintegros/{caso.id}/remitido-isl", json={"fecha_remitido_isl": "2026-11-09"})

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["remitido_isl"], cuerpo["fecha_remitido_isl"], cuerpo["estado_reintegro"]) == (
        True, "2026-11-09", "pendiente",
    )
    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]
    assert ejecutar_job_alertas(db_session, hoy=DIA_7 + datetime.timedelta(days=1)) == 0


@pytest.mark.parametrize("fecha", ["2026-11-01", "2099-01-01"])
def test_la_fecha_de_remision_no_puede_ser_anterior_al_caso_ni_futura(db_session, as_admin, fecha):
    caso = _caso_isl(db_session)

    r = as_admin.patch(f"/api/v1/reintegros/{caso.id}/remitido-isl", json={"fecha_remitido_isl": fecha})

    assert r.status_code == 422
    assert "remisión a ISL" in r.json()["detail"]


def test_el_auditor_no_puede_marcar_remitido(db_session, as_auditor):
    caso = _caso_isl(db_session)

    r = as_auditor.patch(f"/api/v1/reintegros/{caso.id}/remitido-isl", json={"fecha_remitido_isl": "2026-11-09"})

    assert r.status_code == 403


def test_el_cierre_con_remitido_resuelve_y_sin_remitido_borra_la_fecha(db_session, as_admin):
    caso = _caso_isl(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_7)
    cierre = {"estado_reintegro": "parcial", "alta_medica": False, "alta_psicologica": False}

    r = as_admin.patch(f"/api/v1/reintegros/{caso.id}/cierre", json={**cierre, "remitido_isl": True})
    assert r.status_code == 200, r.text
    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]

    as_admin.patch(f"/api/v1/reintegros/{caso.id}/remitido-isl", json={"fecha_remitido_isl": "2026-11-09"})
    r = as_admin.patch(f"/api/v1/reintegros/{caso.id}/cierre", json={**cierre, "remitido_isl": False})
    assert (r.json()["remitido_isl"], r.json()["fecha_remitido_isl"]) == (False, None)


def test_el_listado_de_alertas_trae_el_paciente(db_session, as_coordinacion):
    caso = _caso_isl(db_session)
    ejecutar_job_alertas(db_session, hoy=DIA_7)

    [fila] = [a for a in as_coordinacion.get("/api/v1/alertas").json() if a["tipo"] == TIPO]

    assert (fila["caso_tipo"], fila["caso_id"], fila["paciente_nombre"]) == ("caso_reintegro", caso.id, "Paciente 1")


def test_las_consultas_compilan_en_oracle():
    consulta = (
        select(CasoReintegro.id)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(~_no_requiere_remision())
    )
    sql = str(consulta.compile(dialect=oracle.dialect())).upper()
    assert "IS TRUE" not in sql and "IS FALSE" not in sql


# ── Ocupación y precarga del alta ──────────────────────────────────────────


def _payload(ingreso_id: int, **over) -> dict:
    base = {
        "ingreso_id": ingreso_id, "nombre": "Paciente 1", "tipo_derivacion": "DIAT",
        "fecha_caso": "2026-11-02", "region": "Maule", "tipo_trabajador": "dependiente",
    }
    base.update(over)
    return base


def test_el_caso_guarda_y_edita_la_ocupacion(db_session, as_admin):
    ingreso = _ingreso(db_session, _paciente(db_session))

    r = as_admin.post("/api/v1/reintegros", json=_payload(ingreso.id, ocupacion="  Operario de bodega "))
    assert r.status_code == 201, r.text
    assert r.json()["ocupacion"] == "Operario de bodega"

    r = as_admin.patch(f"/api/v1/reintegros/{r.json()['id']}", json={"ocupacion": "Supervisor"})
    assert r.json()["ocupacion"] == "Supervisor"


def test_la_ocupacion_tiene_maximo_120(db_session, as_admin):
    ingreso = _ingreso(db_session, _paciente(db_session))

    r = as_admin.post("/api/v1/reintegros", json=_payload(ingreso.id, ocupacion="x" * 121))

    assert r.status_code == 422


def test_precarga_desde_un_caso_anterior_del_paciente(db_session, as_admin):
    paciente = _paciente(db_session)
    anterior = _ingreso(db_session, paciente, n=1)
    _caso(db_session, anterior, ocupacion="Temporero", tipo_trabajador="independiente", estado_reintegro="total")
    nuevo = _ingreso(db_session, paciente, n=2)

    r = as_admin.get("/api/v1/reintegros/precarga", params={"ingreso_id": nuevo.id})

    assert r.status_code == 200
    assert r.json() == {"ocupacion": "Temporero", "tipo_trabajador": "independiente"}


def test_precarga_la_ocupacion_desde_salutem(db_session, as_admin):
    db_session.add(SalutemPersona(
        salutem_id=990001, rut="111111111", contenido={"SALUTEM_ID": 990001, "Ocupación": "Profesora"},
        hash_contenido="x", visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
    ))
    paciente = _paciente(db_session, salutem_persona_id=990001)
    ingreso = _ingreso(db_session, paciente)

    r = as_admin.get("/api/v1/reintegros/precarga", params={"ingreso_id": ingreso.id})

    assert r.json() == {"ocupacion": "Profesora", "tipo_trabajador": None}


def test_precarga_vacia_sin_datos(db_session, as_admin):
    ingreso = _ingreso(db_session, _paciente(db_session))

    r = as_admin.get("/api/v1/reintegros/precarga", params={"ingreso_id": ingreso.id})

    assert r.json() == {"ocupacion": None, "tipo_trabajador": None}


@pytest.mark.parametrize(
    ("contenido", "esperado"),
    [
        ({"ocupacion": "Chofer"}, "Chofer"),
        ({"PROFESION": "Ingeniera"}, "Ingeniera"),
        ({"profesion_u_oficio": "Gásfiter"}, "Gásfiter"),
        ({"ocupacion": "   "}, None),
        ({"ocupacion": 3}, None),
        ({"nombres": "Ana"}, None),
        (None, None),
    ],
)
def test_ocupacion_de_la_ficha_de_salutem(contenido, esperado):
    assert ocupacion_de_contenido(contenido) == esperado


# ── Lista global de la pestaña ─────────────────────────────────────────────


def test_el_panel_lista_los_casos_activos_con_proyeccion_y_pendientes(db_session, as_coordinacion):
    isl = _caso_isl(db_session, n=1)
    ingreso_isl = db_session.get(Ingreso, isl.ingreso_id)
    _control(db_session, ingreso_isl, datetime.date(2026, 11, 5), "3 semanas aproximadamente")
    _control(db_session, ingreso_isl, datetime.date(2026, 11, 12), "Paciente con reintegro parcial")
    _control(db_session, ingreso_isl, datetime.date(2026, 11, 15), None)
    clinico = _caso(db_session, _ingreso(db_session, _paciente(db_session, 2), tipo_derivacion="Particular"))
    remitido = _caso_isl(db_session, n=3, remitido_isl=True, fecha_solicitud_reca=FECHA_CASO)
    con_reca = _caso_isl(db_session, n=4)
    db_session.add(Reca(caso_reintegro_id=con_reca.id, fecha_reca=FECHA_CASO, tipo_reca="AT",
                        numero_reca="R-1", razon_social="X"))
    _caso_isl(db_session, n=5, estado_reintegro="total")
    _caso(db_session, _ingreso(db_session, _paciente(db_session, 6), estado="cerrado"))
    db_session.flush()

    r = as_coordinacion.get("/api/v1/reintegros/panel")

    assert r.status_code == 200, r.text
    filas = {f["caso_id"]: f for f in r.json()["activos"]}
    assert set(filas) == {isl.id, clinico.id, remitido.id, con_reca.id}
    f = filas[isl.id]
    assert (f["paciente_nombre"], f["rut"], f["folio"], f["estado_reintegro"]) == (
        "Paciente 1", "111111111", ingreso_isl.folio, "pendiente",
    )
    assert (f["proyeccion"], f["fecha_proyeccion"]) == ("Paciente con reintegro parcial", "2026-11-12")
    assert (f["es_isl"], f["reca_por_solicitar"], f["pendiente_remitir_isl"]) == (True, True, True)
    assert (filas[clinico.id]["es_isl"], filas[clinico.id]["reca_por_solicitar"],
            filas[clinico.id]["pendiente_remitir_isl"]) == (False, False, False)
    assert (filas[remitido.id]["reca_por_solicitar"], filas[remitido.id]["pendiente_remitir_isl"]) == (False, False)
    assert filas[remitido.id]["estado_solicitud_reca"] == "solicitada"
    assert filas[con_reca.id]["estado_solicitud_reca"] == "recibida"
    assert filas[con_reca.id]["reca_por_solicitar"] is False


def test_pendientes_por_registrar(db_session, as_coordinacion):
    # Con alerta abierta y sin caso: aparece (una vez, con el control más reciente).
    sin_caso = _ingreso(db_session, _paciente(db_session, 1))
    _alerta_proyeccion(db_session, _control(db_session, sin_caso, datetime.date(2026, 11, 3), "1 semana aproximadamente"))
    ultimo = _alerta_proyeccion(
        db_session, _control(db_session, sin_caso, datetime.date(2026, 11, 10), "2 semanas aproximadamente")
    )
    # Con caso activo: no aparece.
    con_caso = _ingreso(db_session, _paciente(db_session, 2))
    _caso(db_session, con_caso)
    _alerta_proyeccion(db_session, _control(db_session, con_caso, datetime.date(2026, 11, 10), "1 semana aproximadamente"))
    # Con la alerta resuelta: no aparece.
    resuelta = _ingreso(db_session, _paciente(db_session, 3))
    _alerta_proyeccion(
        db_session, _control(db_session, resuelta, datetime.date(2026, 11, 10), "1 semana aproximadamente"), "resuelta"
    )
    # Con un caso ya terminado (reintegro total): aparece.
    terminado = _ingreso(db_session, _paciente(db_session, 4))
    _caso(db_session, terminado, estado_reintegro="total")
    _alerta_proyeccion(
        db_session, _control(db_session, terminado, datetime.date(2026, 11, 8), "Paciente con reintegro parcial")
    )

    r = as_coordinacion.get("/api/v1/reintegros/panel")

    pendientes = r.json()["pendientes_registro"]
    assert [p["paciente_nombre"] for p in pendientes] == ["Paciente 1", "Paciente 4"]
    p = pendientes[0]
    assert (p["alerta_id"], p["ingreso_id"], p["folio"], p["proyeccion"], p["fecha_control"], p["plazo_estimado"]) == (
        ultimo.id, sin_caso.id, sin_caso.folio, "2 semanas aproximadamente", "2026-11-10", "2026-11-24",
    )
    assert pendientes[1]["plazo_estimado"] is None


def test_el_auditor_lee_el_panel(as_auditor):
    r = as_auditor.get("/api/v1/reintegros/panel")
    assert r.status_code == 200
    assert r.json() == {"activos": [], "pendientes_registro": []}


def test_un_ingreso_con_ept_es_isl_en_el_panel(db_session, as_coordinacion):
    caso = _caso(db_session, _ingreso(db_session, _paciente(db_session), tipo_derivacion="Particular"))
    db_session.add(CasoEpt(
        ingreso_id=caso.ingreso_id, mes="noviembre", fecha_ingreso_ept=FECHA_CASO, nombre_trabajador="X",
        rut_trabajador="111111111", region_trabajador="Maule", eista="E", factor_riesgo="otro",
    ))
    db_session.flush()

    [fila] = as_coordinacion.get("/api/v1/reintegros/panel").json()["activos"]

    assert fila["es_isl"] is True
