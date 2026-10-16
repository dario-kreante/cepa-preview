"""Pacientes borrador creados desde SALUTEM para personas atendidas que no existen en el SIGE."""

from datetime import date

from sqlalchemy import select

from app.config import get_settings
from app.integrations.salutem.models import AtencionSalutem, EstadoCitaSalutem, PersonaSalutem
from app.models.alertas import AlertaNotif
from app.models.audit_log import AuditLog
from app.models.config_alerta import ConfigAlerta
from app.models.paciente import Paciente
from app.services.salutem_sync import borradores, copia
from app.models.salutem_sync import SalutemSyncEjecucion
from app.services.salutem_sync.borradores import crear_borradores
from app.services.salutem_sync.orquestador import correr
from tests.salutem_sync.conftest import AHORA

ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
AGENDADO = int(EstadoCitaSalutem.AGENDADO)
CORTE = date(2026, 9, 1)
PERSONA = 7100


def _persona(db, salutem_id=PERSONA, **datos):
    base = {"SALUTEM_ID": salutem_id, "identificacion": "12345678-5", "tipoIdentificacion": "RUT",
            "nombres": "ANA", "apellidos": "PRUEBA UNO", "sexo": "MUJER"}
    base.update(datos)
    copia.guardar_persona(db, PersonaSalutem.desde_api(base), AHORA)


def _atencion(db, cita_id, persona=PERSONA, fecha="2026-09-10", estado=ATENDIDO):
    copia.guardar_atencion(db, AtencionSalutem.desde_api({
        "personaId": persona, "citaId": cita_id, "citaFecha": fecha, "estadoCitaId": estado,
        "estadoCitaNombre": "Atendido", "especialidadNombre": "Médico/a",
    }), AHORA)


def _atendida(db, salutem_id=PERSONA, cita_id=None, **datos):
    _persona(db, salutem_id, **datos)
    _atencion(db, cita_id or salutem_id * 10, persona=salutem_id)


def _pacientes(db):
    return list(db.scalars(select(Paciente).order_by(Paciente.id)))


def _alertas(db):
    return list(db.scalars(select(AlertaNotif)))


def test_crea_un_borrador_por_persona_atendida_desde_el_corte(db_session):
    _atendida(db_session)

    r = crear_borradores(db_session, AHORA, CORTE)

    assert (r.creados, r.errores) == (1, [])
    [p] = _pacientes(db_session)
    assert (p.estado_registro, p.origen, p.salutem_persona_id) == ("pendiente_folio", "SALUTEM", PERSONA)
    [a] = _alertas(db_session)
    assert (a.tipo, a.caso_tipo, a.caso_id, a.usuario_id, a.ventana_dias, a.estado) == (
        "paciente_pendiente_folio", "paciente", p.id, None, 0, "pendiente")
    auditoria = db_session.scalars(select(AuditLog).where(AuditLog.entity == "paciente")).all()
    assert [(x.actor, x.action) for x in auditoria] == [("sistema:salutem-sync", "CREATE")]


def test_mapea_los_datos_de_salutem(db_session):
    _atendida(db_session, nombres="HUMBERTO", apellidos="ESCOBAR PRUEBA", identificacion="12345678-5",
              sexo="HOMBRE", fechaNacimiento="14-07-1967", comuna="Talca")

    crear_borradores(db_session, AHORA, CORTE)

    [p] = _pacientes(db_session)
    assert p.nombre == "HUMBERTO ESCOBAR PRUEBA"
    assert p.rut == "123456785"
    assert p.sexo == "M"
    assert p.edad == 59
    assert p.comuna == "Talca"
    assert p.region is None


def test_persona_sin_rut_queda_sin_rut(db_session):
    _atendida(db_session, 7101, identificacion="sin_id_1141409", tipoIdentificacion="SIN IDENTIFICACION")
    _atendida(db_session, 7102, identificacion="11111111-2", sexo="HOMBRE")
    _atendida(db_session, 7103, sexo="otra cosa")
    _atendida(db_session, 7104, identificacion=None)

    crear_borradores(db_session, AHORA, CORTE)

    por_persona = {p.salutem_persona_id: p for p in _pacientes(db_session)}
    assert por_persona[7101].rut is None
    assert por_persona[7102].rut is None  # RUT inválido
    assert por_persona[7101].sexo == "F"
    assert por_persona[7103].sexo == "otro"
    assert por_persona[7101].edad is None  # sin fecha de nacimiento
    assert por_persona[7104].rut is None


def test_sin_corte_no_crea_nada(db_session):
    _atendida(db_session)

    r = crear_borradores(db_session, AHORA, None)

    assert (r.creados, r.errores) == (0, [])
    assert _pacientes(db_session) == [] and _alertas(db_session) == []


def test_ignora_atenciones_anteriores_al_corte_y_no_atendidas(db_session):
    _persona(db_session, 7201)
    _atencion(db_session, 72011, persona=7201, fecha="2026-08-31")
    _persona(db_session, 7202)
    _atencion(db_session, 72021, persona=7202, estado=AGENDADO)

    r = crear_borradores(db_session, AHORA, CORTE)

    assert r.creados == 0
    assert _pacientes(db_session) == []


def test_no_duplica_en_el_ciclo_siguiente(db_session):
    _atendida(db_session)

    crear_borradores(db_session, AHORA, CORTE)
    r = crear_borradores(db_session, AHORA, CORTE)

    assert r.creados == 0
    assert len(_pacientes(db_session)) == 1 and len(_alertas(db_session)) == 1


def test_no_recrea_un_descartado(db_session):
    _atendida(db_session)
    crear_borradores(db_session, AHORA, CORTE)
    [p] = _pacientes(db_session)
    p.estado_registro = "descartado"
    db_session.flush()

    r = crear_borradores(db_session, AHORA, CORTE)

    assert r.creados == 0
    assert len(_pacientes(db_session)) == 1


def test_no_crea_si_ya_cruza_con_un_paciente_por_rut_o_por_id(db_session):
    db_session.add(Paciente(rut="123456785", nombre="Existente", sexo="F", edad=30, region="Maule"))
    db_session.add(Paciente(rut="390000099", nombre="Por id", sexo="F", edad=30, region="Maule",
                            salutem_persona_id=7302))
    _atendida(db_session, 7301)  # identificación 12345678-5: cruza por RUT
    _atendida(db_session, 7302, identificacion="sin_id_1", tipoIdentificacion="SIN IDENTIFICACION")
    db_session.flush()

    r = crear_borradores(db_session, AHORA, CORTE)

    assert r.creados == 0
    assert len(_pacientes(db_session)) == 2


def test_tipo_de_alerta_apagado_crea_el_borrador_sin_alerta(db_session):
    db_session.add(ConfigAlerta(tipo="paciente_pendiente_folio", dias=0, habiles=False, activo=False))
    _atendida(db_session)
    db_session.flush()

    r = crear_borradores(db_session, AHORA, CORTE)

    assert r.creados == 1
    assert len(_pacientes(db_session)) == 1
    assert _alertas(db_session) == []


def test_un_error_en_una_persona_no_detiene_a_las_demas(db_session, monkeypatch):
    _atendida(db_session, 7401, identificacion="sin_id_1", tipoIdentificacion="SIN IDENTIFICACION")
    _atendida(db_session, 7402, identificacion="sin_id_2", tipoIdentificacion="SIN IDENTIFICACION")
    original = borradores.paciente_desde_persona

    def falla_en_la_primera(persona, hoy):
        if persona.salutem_id == 7401:
            raise RuntimeError("datos raros")
        return original(persona, hoy)

    monkeypatch.setattr(borradores, "paciente_desde_persona", falla_en_la_primera)

    r = crear_borradores(db_session, AHORA, CORTE)

    assert r.creados == 1
    assert len(r.errores) == 1 and "7401" in r.errores[0] and "datos raros" in r.errores[0]
    assert [p.salutem_persona_id for p in _pacientes(db_session)] == [7402]


def test_corte_invalido_no_crea_y_registra_el_error(db_session, salutem, ritmo, monkeypatch):
    monkeypatch.setattr(get_settings(), "salutem_borradores_desde", "16/10/2026")
    _atendida(db_session)

    assert correr("caliente", db_session, salutem, ritmo, ahora=lambda: AHORA, habilitado=True, dueno="test") == 0

    assert _pacientes(db_session) == []
    ejecucion = db_session.scalars(select(SalutemSyncEjecucion)).one()
    assert ejecucion.estado == "con_errores"
    assert "16/10/2026" in ejecucion.error


def test_corte_vacio_o_valido_desde_el_setting(db_session, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "salutem_borradores_desde", "")
    assert s.salutem_borradores_desde_fecha is None
    monkeypatch.setattr(s, "salutem_borradores_desde", "2026-09-01")
    assert s.salutem_borradores_desde_fecha == CORTE


def test_resolver_alerta_borrador_resuelve_las_abiertas(db_session):
    _atendida(db_session)
    crear_borradores(db_session, AHORA, CORTE)
    [p] = _pacientes(db_session)

    borradores.resolver_alerta_borrador(db_session, p.id)

    [a] = _alertas(db_session)
    assert a.estado == "resuelta"


def _sql_ejecutado(db, fn):
    """Ejecuta fn y devuelve los SELECT enviados a la BD."""
    sentencias: list[str] = []

    def capturar(conn, cursor, statement, parameters, context, executemany):
        sentencias.append(statement)

    from sqlalchemy import event

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", capturar)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", capturar)
    return sentencias


def test_candidatas_no_usa_listas_in_literales(db_session):
    """Oracle admite máximo 1000 elementos en un IN (ORA-01795): debe ser subconsulta/join."""
    import re

    for i in range(3):
        _atendida(db_session, salutem_id=7200 + i)

    sentencias = _sql_ejecutado(db_session, lambda: borradores._candidatas(db_session, CORTE))

    assert sentencias
    for s in sentencias:
        assert not re.search(r"\bIN\s*\(\s*(%\(|\$\d|\?|:)", s, re.IGNORECASE), s
