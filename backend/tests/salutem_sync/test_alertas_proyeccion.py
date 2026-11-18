"""Alerta «Proyección de reintegro registrada» (QA-003, 18-11-2026).

Cuando la sincronización deja un control con ``proyeccion_reintegro`` con un valor real
(«Más de 1 mes», o cualquier otro: la lista de SALUTEM no es conocida por completo) se avisa
una vez por control y valor. El relleno del ambiente de capacitación y los vacíos no alertan.
"""

from sqlalchemy import select

from app.models.alertas import AlertaNotif
from app.models.config_alerta import ConfigAlerta
from app.models.control_medico import ControlMedico
from app.services.salutem_sync.alertas_control import huella_proyeccion
from app.services.salutem_sync.vinculacion import vincular
from tests.salutem_sync.conftest import AHORA
from tests.salutem_sync.test_alertas_control import _atencion, _ingreso

TIPO = "proyeccion_reintegro"
RELLENO = "antecedente de prueba para ambiente de capacitación"


def _proyeccion(valor: str) -> dict:
    return {
        "indicaciones": [
            {"agrupacion": "Indicaciones", "nombre": "Proyección de reintegro laboral", "registro": [valor]}
        ]
    }


def _alertas(db) -> list[AlertaNotif]:
    return list(db.scalars(select(AlertaNotif).where(AlertaNotif.tipo == TIPO).order_by(AlertaNotif.id)))


def test_proyeccion_real_crea_una_alerta_sobre_el_control(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8001, **_proyeccion("Más de 1 mes"))

    vincular(db_session, AHORA)

    [control] = db_session.scalars(select(ControlMedico)).all()
    assert control.proyeccion_reintegro == "Más de 1 mes"
    [a] = _alertas(db_session)
    assert (a.caso_tipo, a.caso_id, a.estado, a.ventana_dias) == (
        "control_medico", control.id, "pendiente", huella_proyeccion("Más de 1 mes"),
    )


def test_acepta_cualquier_valor_sin_lista_cerrada(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8002, **_proyeccion("Entre 2 y 3 semanas"))

    vincular(db_session, AHORA)

    assert len(_alertas(db_session)) == 1


def test_el_relleno_de_capacitacion_no_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8003, **_proyeccion(RELLENO))

    vincular(db_session, AHORA)

    assert _alertas(db_session) == []


def test_el_relleno_con_otra_grafia_no_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8004, **_proyeccion("  Antecedente de prueba para ambiente de CAPACITACION. "))

    vincular(db_session, AHORA)

    assert _alertas(db_session) == []


def test_sin_proyeccion_o_vacia_no_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8005, **_proyeccion("   "))
    vincular(db_session, AHORA)
    assert _alertas(db_session) == []


def test_revincular_sin_cambios_no_duplica(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8006, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    _atencion(db_session, 8006, **_proyeccion("Más de 1 mes"),
              evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)

    assert len(_alertas(db_session)) == 1


def test_una_alerta_resuelta_no_reaparece_con_el_mismo_valor(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8007, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    [a] = _alertas(db_session)
    a.estado = "resuelta"
    db_session.flush()
    _atencion(db_session, 8007, **_proyeccion("Más de 1 mes"),
              evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)

    assert [x.estado for x in _alertas(db_session)] == ["resuelta"]


def test_si_el_medico_cambia_la_proyeccion_se_avisa_de_nuevo(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8008, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    _atencion(db_session, 8008, **_proyeccion("Menos de 1 mes"))

    vincular(db_session, AHORA)

    alertas = _alertas(db_session)
    assert [x.ventana_dias for x in alertas] == [huella_proyeccion("Más de 1 mes"), huella_proyeccion("Menos de 1 mes")]
    # La del valor anterior ya no es vigente: queda resuelta para no mostrar un valor viejo.
    assert [x.estado for x in alertas] == ["resuelta", "pendiente"]


def test_volver_a_un_valor_ya_alertado_no_crea_otra(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8009, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    _atencion(db_session, 8009, **_proyeccion("Menos de 1 mes"))
    vincular(db_session, AHORA)
    _atencion(db_session, 8009, **_proyeccion("Más de 1 mes"))

    vincular(db_session, AHORA)

    assert len(_alertas(db_session)) == 2


def test_si_la_proyeccion_queda_vacia_se_resuelve_la_alerta_abierta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8010, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    _atencion(db_session, 8010, **_proyeccion(RELLENO))

    vincular(db_session, AHORA)

    assert [x.estado for x in _alertas(db_session)] == ["resuelta"]


def test_control_antiguo_no_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 8011, fecha="2026-08-20", **_proyeccion("Más de 1 mes"))

    vincular(db_session, AHORA, todo=True)

    assert _alertas(db_session) == []


def test_caso_cerrado_no_alerta(db_session):
    ingreso = _ingreso(db_session)
    ingreso.estado = "cerrado"
    db_session.flush()
    _atencion(db_session, 8012, **_proyeccion("Más de 1 mes"))

    vincular(db_session, AHORA)

    assert _alertas(db_session) == []


def test_tipo_apagado_en_la_configuracion_no_alerta(db_session):
    _ingreso(db_session)
    db_session.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == TIPO)).activo = False
    db_session.flush()
    _atencion(db_session, 8013, **_proyeccion("Más de 1 mes"))

    vincular(db_session, AHORA)

    assert _alertas(db_session) == []


def test_no_interfiere_con_las_alertas_de_licencia_y_receta(db_session):
    from tests.salutem_sync.test_alertas_control import LICENCIA

    _ingreso(db_session)
    _atencion(db_session, 8014, **LICENCIA, **_proyeccion("Más de 1 mes"))

    vincular(db_session, AHORA)

    tipos = sorted(a.tipo for a in db_session.scalars(select(AlertaNotif)))
    assert tipos == ["licencia_en_control", TIPO]


def test_al_cerrar_el_ingreso_se_resuelve_la_alerta(db_session):
    from app.services.alertas_cierre import resolver_alertas_de_ingreso

    ingreso = _ingreso(db_session)
    _atencion(db_session, 8015, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)

    resolver_alertas_de_ingreso(db_session, ingreso.id)

    assert [a.estado for a in _alertas(db_session)] == ["resuelta"]


def test_el_listado_muestra_el_valor_y_el_paciente(db_session, as_coordinacion):
    _ingreso(db_session)
    _atencion(db_session, 8020, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    [control] = db_session.scalars(select(ControlMedico)).all()

    [fila] = [a for a in as_coordinacion.get("/api/v1/alertas").json() if a["tipo"] == TIPO]

    assert (fila["detalle"], fila["caso_tipo"], fila["caso_id"]) == ("Más de 1 mes", "control_medico", control.id)
    assert fila["paciente_nombre"] == "Paciente Alerta"
    assert fila["paciente_id"] is not None


def test_el_listado_muestra_el_valor_nuevo_tras_el_cambio(db_session, as_coordinacion):
    _ingreso(db_session)
    _atencion(db_session, 8021, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    _atencion(db_session, 8021, **_proyeccion("Menos de 1 mes"))
    vincular(db_session, AHORA)

    filas = [a for a in as_coordinacion.get("/api/v1/alertas").json() if a["tipo"] == TIPO]

    abiertas = [f for f in filas if f["estado"] == "pendiente"]
    assert [f["detalle"] for f in abiertas] == ["Menos de 1 mes"]


def test_el_contexto_de_la_alerta_abre_el_control(db_session, as_coordinacion):
    _ingreso(db_session)
    _atencion(db_session, 8022, **_proyeccion("Más de 1 mes"))
    vincular(db_session, AHORA)
    [a] = _alertas(db_session)

    r = as_coordinacion.get(f"/api/v1/alertas/{a.id}/contexto")

    assert r.status_code == 200 and r.json()["paciente_nombre"] == "Paciente Alerta"


def test_las_consultas_compilan_en_oracle():
    from sqlalchemy.dialects import oracle  # noqa: PLC0415

    consulta = select(AlertaNotif).where(
        AlertaNotif.caso_tipo == "control_medico",
        AlertaNotif.caso_id == 1,
        AlertaNotif.tipo == TIPO,
        AlertaNotif.estado.in_(("pendiente", "leida")),
    )
    sql = str(consulta.compile(dialect=oracle.dialect()))
    assert "IS TRUE" not in sql.upper()
