"""Dashboard operativo: atenciones desde la copia de SALUTEM + pendientes de gestión."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.alertas import AlertaNotif
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemCita
from app.services.dashboard_operativo import resumen_operativo

HOY = date(2026, 10, 16)  # viernes
_AHORA = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)

_ING = dict(
    folio_manual=True,
    tipo_derivacion="DIAT",
    tipo_ingreso="convenio",
    modelo_tratamiento="ambulatorio",
    diagnostico="Test",
)


def _cita(cita_id: int, fecha: date, estado: int, **contenido) -> SalutemCita:
    return SalutemCita(
        cita_id=cita_id,
        persona_id=1,
        fecha_cita=fecha,
        estado_id=estado,
        contenido=contenido,
        hash_contenido="x" * 64,
        visto_primera_vez=_AHORA,
        visto_ultima_vez=_AHORA,
        cambiado_en=_AHORA,
    )


def _licencia(ingreso_id: int, inicio: date, termino: date, **extra) -> LicenciaMedica:
    return LicenciaMedica(
        ingreso_id=ingreso_id, tipo_lm="1", tipo_reposo="total", cantidad_dias=10,
        origen="sistema", fecha_inicio=inicio, fecha_termino=termino, fecha_emision=inicio,
        inicio_reposo=inicio, fin_reposo=termino, diagnostico="Test", **extra,
    )


@pytest.fixture
def datos(db_session):
    pac = Paciente(rut="11111111-1", nombre="Pac", sexo="F", edad=30, region="Maule")
    borrador = Paciente(nombre="Borrador", estado_registro="pendiente_folio", origen="SALUTEM")
    db_session.add_all([pac, borrador])
    db_session.flush()

    activo = Ingreso(**_ING, paciente_id=pac.id, folio="F-OP-1", programa="DIAT",
                     fecha_ingreso=HOY - timedelta(days=5))
    viejo = Ingreso(**_ING, paciente_id=pac.id, folio="F-OP-2", programa="DIEP",
                    fecha_ingreso=HOY - timedelta(days=200))
    cerrado = Ingreso(**_ING, paciente_id=pac.id, folio="F-OP-3", programa="DIAT",
                      fecha_ingreso=HOY - timedelta(days=90), estado="cerrado",
                      fecha_alta=HOY - timedelta(days=3))
    db_session.add_all([activo, viejo, cerrado])
    db_session.flush()

    db_session.add_all([
        # Período: atendidas (2 psicología, 1 medicina), 1 inasistencia, 1 anulada.
        _cita(1, HOY - timedelta(days=1), 3, especialidadNombre="Psicología", profesionalNombre="Ana"),
        _cita(2, HOY - timedelta(days=2), 3, especialidadNombre="Psicología", profesionalNombre="Ana"),
        _cita(3, HOY - timedelta(days=8), 3, especialidadNombre="Medicina", profesionalNombre="Luis"),
        _cita(4, HOY - timedelta(days=3), 9),
        _cita(5, HOY - timedelta(days=4), 2),
        # Fuera del período por defecto (30 días).
        _cita(6, HOY - timedelta(days=45), 3, especialidadNombre="Psicología"),
        # Agenda próxima: 2 vigentes en 7 días, 1 anulada y 1 más lejos no cuentan.
        _cita(7, HOY, 1),
        _cita(8, HOY + timedelta(days=6), 5),
        _cita(9, HOY + timedelta(days=2), 2),
        _cita(10, HOY + timedelta(days=7), 1),
    ])
    # Cita que desapareció de SALUTEM: no cuenta.
    fantasma = _cita(11, HOY - timedelta(days=1), 3)
    fantasma.desaparecida_en = _AHORA
    db_session.add(fantasma)

    db_session.add_all([
        _licencia(activo.id, HOY - timedelta(days=2), HOY + timedelta(days=5)),  # activa, ISL pendiente
        _licencia(activo.id, HOY - timedelta(days=30), HOY - timedelta(days=20),
                  envio_isl="enviado", fecha_envio_isl=HOY - timedelta(days=19)),
        _licencia(activo.id, HOY - timedelta(days=1), HOY + timedelta(days=1), anulada=True),
        Oda(ingreso_id=activo.id, identificador="ODA-1", fecha_vencimiento=HOY - timedelta(days=1)),
        Oda(ingreso_id=activo.id, identificador="ODA-2", fecha_vencimiento=HOY + timedelta(days=10)),
        Oda(ingreso_id=activo.id, identificador="ODA-3", fecha_vencimiento=HOY + timedelta(days=40)),
        Oda(ingreso_id=cerrado.id, identificador="ODA-4", fecha_vencimiento=HOY - timedelta(days=1)),
    ])
    for tipo, estado in [("oda_por_vencer", "pendiente"), ("oda_por_vencer", "leida"),
                         ("licencia_en_control", "pendiente"), ("plazo_isl", "resuelta")]:
        db_session.add(AlertaNotif(
            tipo=tipo, estado=estado, caso_id=1, caso_tipo="oda",
            plazo_objetivo=_AHORA, ventana_dias=7, email_enviado=False,
        ))
    db_session.commit()


def test_resumen_operativo_periodo_por_defecto(db_session, datos):
    r = resumen_operativo(db_session, hoy=HOY)

    assert r.periodo_desde == HOY - timedelta(days=29)
    assert r.periodo_hasta == HOY
    assert (r.pacientes_activos, r.ingresos_periodo, r.altas_periodo) == (2, 1, 1)
    assert (r.atenciones, r.inasistencias, r.anulaciones) == (3, 1, 1)
    assert r.tasa_inasistencia == 25.0
    assert r.agendadas_proximas == 2
    assert [(c.etiqueta, c.total) for c in r.atenciones_por_especialidad] == [
        ("Psicología", 2), ("Medicina", 1),
    ]
    assert [(c.etiqueta, c.total) for c in r.atenciones_por_profesional] == [("Ana", 2), ("Luis", 1)]
    assert [(c.etiqueta, c.total) for c in r.activos_por_programa] == [("DIAT", 1), ("DIEP", 1)]

    assert (r.licencias_activas, r.licencias_pendientes_isl) == (1, 1)
    assert (r.odas_vencidas, r.odas_por_vencer) == (1, 1)
    assert r.pacientes_pendientes_folio == 1
    assert r.alertas_abiertas == 3
    assert [(c.etiqueta, c.total) for c in r.alertas_por_tipo] == [
        ("oda_por_vencer", 2), ("licencia_en_control", 1),
    ]


def test_tendencia_semanal_agrupa_por_lunes(db_session, datos):
    r = resumen_operativo(db_session, hoy=HOY)

    assert len(r.tendencia_semanal) == 8
    ultima = r.tendencia_semanal[-1]
    assert ultima.semana == date(2026, 10, 12)
    # Semana del 12-10: atendidas el 14 y 15, inasistencia el 13.
    assert (ultima.atendidas, ultima.inasistencias) == (2, 1)
    anterior = r.tendencia_semanal[-2]
    assert (anterior.semana, anterior.atendidas, anterior.inasistencias) == (date(2026, 10, 5), 1, 0)


def test_periodo_explicito_y_sin_datos(db_session, datos):
    r = resumen_operativo(db_session, date(2026, 1, 1), date(2026, 1, 31), hoy=HOY)
    assert (r.atenciones, r.inasistencias, r.ingresos_periodo) == (0, 0, 0)
    assert r.tasa_inasistencia is None
    assert r.atenciones_por_especialidad == []


def test_endpoint_operativo(as_auditor, datos):
    resp = as_auditor.get("/api/v1/dashboard/operativo")
    assert resp.status_code == 200
    body = resp.json()
    assert {"atenciones", "tendencia_semanal", "alertas_por_tipo"} <= body.keys()


def test_endpoint_operativo_rango_invalido(as_coordinacion):
    resp = as_coordinacion.get(
        "/api/v1/dashboard/operativo", params={"fecha_desde": "2026-02-01", "fecha_hasta": "2026-01-01"}
    )
    assert resp.status_code == 422


def test_endpoint_operativo_sin_token(client):
    assert client.get("/api/v1/dashboard/operativo").status_code == 401
