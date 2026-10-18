"""Catálogo de profesionales armado desde la copia local de SALUTEM (sin llamadas a la API)."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, EstadoCitaSalutem, PersonaSalutem
from app.models.audit_log import AuditLog
from app.models.control_medico import ControlMedico
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.salutem_sync import SalutemSyncEjecucion
from app.services.salutem_sync import copia, orquestador
from app.services.salutem_sync.orquestador import correr
from app.services.salutem_sync.profesionales import ResultadoProfesionales, sincronizar_profesionales
from app.services.salutem_sync.vinculacion import vincular
from tests.salutem_sync.conftest import AHORA


def _sin_zona(valor: datetime) -> datetime:
    """Postgres devuelve aware y Oracle naive (en UTC): compara ambos sin tzinfo."""
    return valor.astimezone(timezone.utc).replace(tzinfo=None) if valor.tzinfo else valor

ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
AGENDADO = int(EstadoCitaSalutem.AGENDADO)
PERSONA = 8800
ANTES = AHORA - timedelta(days=3)


def _crudo(cita_id, fecha, *, prof=3090, nombre="DRA. PAULA ROJAS", esp="Médico/a", suc="Talca",
           estado=ATENDIDO, persona=PERSONA):
    return {
        "personaId": persona, "citaId": cita_id, "citaFecha": fecha, "estadoCitaId": estado,
        "estadoCitaNombre": "x", "especialidadNombre": esp, "especialidadId": 7,
        "profesionalId": prof, "profesionalNombre": nombre, "sucursalId": 1, "sucursalNombre": suc,
    }


def _atencion(db, *args, ahora=AHORA, **kw):
    copia.guardar_atencion(db, AtencionSalutem.desde_api(_crudo(*args, **kw)), ahora)


def _cita(db, *args, ahora=AHORA, **kw):
    copia.guardar_cita(db, CitaSalutem.desde_api(_crudo(*args, **kw)), ahora)


def _todos(db):
    return list(db.scalars(select(Profesional).order_by(Profesional.id)))


def _por_salutem(db, pid):
    return db.scalar(select(Profesional).where(Profesional.salutem_profesional_id == pid))


def test_crea_el_profesional_con_los_datos_de_salutem(db_session):
    _atencion(db_session, 1, "2026-09-01", esp="Médico/a", suc="Talca")
    _atencion(db_session, 2, "2026-09-10", esp="Evaluación médica", suc="Curicó")
    _cita(db_session, 3, "2026-10-05", estado=AGENDADO)  # no atendida: no cuenta para las fechas

    r = sincronizar_profesionales(db_session, AHORA, None)

    assert (r.creados, r.actualizados, r.adoptados, r.errores) == (1, 0, 0, [])
    [p] = _todos(db_session)
    assert (p.nombre, p.origen, p.activo, p.salutem_profesional_id) == ("DRA. PAULA ROJAS", "SALUTEM", True, 3090)
    assert sorted(p.especialidades) == ["Evaluación médica", "Médico/a"]
    assert sorted(p.sucursales) == ["Curicó", "Talca"]
    assert (p.primera_atencion, p.ultima_atencion) == (date(2026, 9, 1), date(2026, 9, 10))
    # Oracle devuelve la fecha sin zona (en UTC): se compara sin tzinfo.
    assert _sin_zona(p.sincronizado_en) == _sin_zona(AHORA)
    # Sin especialidad previa, toma la más frecuente (empate: la primera en orden alfabético).
    assert p.especialidad in {"Médico/a", "Evaluación médica"}
    auditoria = db_session.scalars(select(AuditLog).where(AuditLog.entity == "profesional")).all()
    assert [(x.actor, x.action) for x in auditoria] == [("sistema:salutem-sync", "CREATE")]


def test_especialidad_libre_toma_la_mas_frecuente_y_no_pisa_la_manual(db_session):
    _atencion(db_session, 1, "2026-09-01", esp="Médico/a")
    _atencion(db_session, 2, "2026-09-02", esp="Médico/a")
    _atencion(db_session, 3, "2026-09-03", esp="Evaluación médica")
    sincronizar_profesionales(db_session, AHORA, None)
    assert _por_salutem(db_session, 3090).especialidad == "Médico/a"

    _por_salutem(db_session, 3090).especialidad = "Psiquiatría"
    _atencion(db_session, 4, "2026-09-04", esp="Evaluación médica")
    sincronizar_profesionales(db_session, AHORA, None)
    assert _por_salutem(db_session, 3090).especialidad == "Psiquiatría"


def test_adopta_por_nombre_sin_tildes_ni_mayusculas_ni_espacios_dobles(db_session):
    existente = Profesional(nombre="Dra.  Paula   Rójas", origen="SALUTEM", activo=False)
    otro = Profesional(nombre="Dr. Manual", origen="SIGE", activo=True)
    db_session.add_all([existente, otro])
    db_session.flush()
    _atencion(db_session, 1, "2026-09-01", nombre="dra. paula rojas")

    r = sincronizar_profesionales(db_session, AHORA, None)

    assert (r.creados, r.adoptados, r.errores) == (0, 1, [])
    assert len(_todos(db_session)) == 2
    db_session.refresh(existente)
    assert existente.salutem_profesional_id == 3090
    # Adoptar no reactiva: la baja manual se respeta.
    assert existente.activo is False


def test_alta_por_id_distinto_crea_otro_profesional(db_session):
    _atencion(db_session, 1, "2026-09-01", prof=3090, nombre="DRA. PAULA ROJAS")
    _atencion(db_session, 2, "2026-09-02", prof=3091, nombre="DR. LUIS SOTO")

    r = sincronizar_profesionales(db_session, AHORA, None)

    assert r.creados == 2
    assert {p.salutem_profesional_id for p in _todos(db_session)} == {3090, 3091}


def test_cambio_de_nombre_en_salutem_actualiza_el_catalogo(db_session):
    _atencion(db_session, 1, "2026-09-01", nombre="DRA. PAULA ROJAS")
    sincronizar_profesionales(db_session, AHORA, None)

    _atencion(db_session, 2, "2026-09-20", nombre="DRA. PAULA ROJAS MUÑOZ")
    r = sincronizar_profesionales(db_session, AHORA, None)

    assert (r.creados, r.actualizados, r.errores) == (0, 1, [])
    [p] = _todos(db_session)
    assert p.nombre == "DRA. PAULA ROJAS MUÑOZ"


def test_cambio_de_nombre_que_choca_deja_el_nombre_y_registra_el_error(db_session):
    _atencion(db_session, 1, "2026-09-01", nombre="DRA. PAULA ROJAS")
    sincronizar_profesionales(db_session, AHORA, None)
    db_session.add(Profesional(nombre="OTRO NOMBRE", origen="SIGE", activo=True))
    db_session.flush()

    _atencion(db_session, 2, "2026-09-20", nombre="OTRO NOMBRE")
    r = sincronizar_profesionales(db_session, AHORA, None)

    assert len(r.errores) == 1 and "3090" in r.errores[0]
    assert _por_salutem(db_session, 3090).nombre == "DRA. PAULA ROJAS"


def test_no_toca_activo_de_un_profesional_dado_de_baja(db_session):
    _atencion(db_session, 1, "2026-09-01")
    sincronizar_profesionales(db_session, AHORA, None)
    _por_salutem(db_session, 3090).activo = False
    _atencion(db_session, 2, "2026-09-02", esp="Otra")

    sincronizar_profesionales(db_session, AHORA, None)

    p = _por_salutem(db_session, 3090)
    assert p.activo is False
    assert "Otra" in p.especialidades


def test_es_idempotente(db_session):
    _atencion(db_session, 1, "2026-09-01")
    sincronizar_profesionales(db_session, AHORA, None)

    r = sincronizar_profesionales(db_session, AHORA, None)

    assert (r.creados, r.actualizados, r.adoptados, r.errores) == (0, 0, 0, [])


def test_incremental_solo_mira_lo_cambiado_y_el_completo_todo(db_session):
    _atencion(db_session, 1, "2026-08-01", prof=3090, ahora=ANTES)
    _atencion(db_session, 2, "2026-09-10", prof=3091, nombre="DR. LUIS SOTO", ahora=AHORA)

    r = sincronizar_profesionales(db_session, AHORA, AHORA - timedelta(days=1))
    assert r.creados == 1
    assert [p.salutem_profesional_id for p in _todos(db_session)] == [3091]

    r = sincronizar_profesionales(db_session, AHORA, None)
    assert r.creados == 1
    assert {p.salutem_profesional_id for p in _todos(db_session)} == {3090, 3091}


def test_incremental_acumula_sobre_lo_ya_guardado(db_session):
    _atencion(db_session, 1, "2026-08-01", esp="Médico/a", suc="Talca", ahora=ANTES)
    sincronizar_profesionales(db_session, ANTES, None)
    _atencion(db_session, 2, "2026-09-10", esp="Evaluación médica", suc="Curicó", ahora=AHORA)

    sincronizar_profesionales(db_session, AHORA, AHORA - timedelta(days=1))

    p = _por_salutem(db_session, 3090)
    assert sorted(p.especialidades) == ["Evaluación médica", "Médico/a"]
    assert sorted(p.sucursales) == ["Curicó", "Talca"]
    assert (p.primera_atencion, p.ultima_atencion) == (date(2026, 8, 1), date(2026, 9, 10))


def test_ignora_filas_sin_profesional_o_desaparecidas(db_session):
    crudo = _crudo(1, "2026-09-01")
    del crudo["profesionalId"]
    copia.guardar_atencion(db_session, AtencionSalutem.desde_api(crudo), AHORA)
    _atencion(db_session, 2, "2026-09-02", prof=3095, nombre="DR. FANTASMA")
    copia.marcar_atencion_desaparecida(db_session, 2, AHORA)

    r = sincronizar_profesionales(db_session, AHORA, None)

    assert r.creados == 0 and _todos(db_session) == []


def _ingreso(db):
    paciente = Paciente(
        rut="390000022", nombre="Paciente Prueba", sexo="F", edad=35, region="Maule",
        salutem_persona_id=PERSONA,
    )
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(
        paciente_id=paciente.id, folio="F-2026-0070", folio_manual=True, fecha_ingreso=date(2026, 6, 1),
        tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="prueba", estado="activo", 
    )
    db.add(ingreso)
    db.flush()
    copia.guardar_persona(
        db,
        PersonaSalutem.desde_api(
            {"SALUTEM_ID": PERSONA, "identificacion": "39000002-2", "tipoIdentificacion": "RUT"}
        ),
        AHORA,
    )
    return ingreso


def test_revincula_controles_y_fichas_con_profesional_nulo(db_session):
    ingreso = _ingreso(db_session)
    _atencion(db_session, 11, "2026-09-01")
    vincular(db_session, AHORA, todo=True)
    control = db_session.scalar(select(ControlMedico).where(ControlMedico.salutem_cita_id == 11))
    ficha = db_session.scalar(select(FichaClinica).where(FichaClinica.salutem_cita_id == 11))
    # El catálogo aún no tenía al profesional: quedan sin vincular.
    assert control.profesional_id is None and ficha.profesional_id is None
    manual = ControlMedico(
        ingreso_id=ingreso.id, fecha_control=date(2026, 9, 2), semana_control=1,
        medico_tratante="Manual", region_derivacion="Maule", origen="CEPA",
    )
    db_session.add(manual)
    db_session.flush()

    r = sincronizar_profesionales(db_session, AHORA, None)

    profesional = _por_salutem(db_session, 3090)
    db_session.refresh(control)
    db_session.refresh(ficha)
    db_session.refresh(manual)
    assert control.profesional_id == profesional.id
    assert ficha.profesional_id == profesional.id
    assert manual.profesional_id is None
    assert r.vinculados == 2


def test_vincular_asigna_profesional_si_ya_esta_en_el_catalogo(db_session):
    _ingreso(db_session)
    p = Profesional(nombre="DRA. PAULA ROJAS", origen="SALUTEM", activo=True, salutem_profesional_id=3090)
    db_session.add(p)
    db_session.flush()
    _atencion(db_session, 11, "2026-09-01")

    vincular(db_session, AHORA, todo=True)

    control = db_session.scalar(select(ControlMedico).where(ControlMedico.salutem_cita_id == 11))
    ficha = db_session.scalar(select(FichaClinica).where(FichaClinica.salutem_cita_id == 11))
    assert control.profesional_id == p.id
    assert ficha.profesional_id == p.id


def test_el_ciclo_corre_el_paso_con_el_inicio_de_la_ultima_ejecucion_exitosa(db_session, salutem, ritmo, monkeypatch):
    previo = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
    db_session.add(SalutemSyncEjecucion(modo="caliente", estado="ok", inicio=previo, llamadas=0))
    db_session.flush()
    llamadas = []
    monkeypatch.setattr(
        orquestador, "sincronizar_profesionales",
        lambda db, ahora, desde: llamadas.append((ahora, desde)) or ResultadoProfesionales(),
    )

    for modo in ("caliente", "backfill"):
        correr(modo, db_session, salutem, ritmo, ahora=lambda: AHORA, habilitado=True, dueno="t")

    # Incremental en caliente; recorrido completo (desde=None) en backfill.
    assert _sin_zona(llamadas[0][1]) == _sin_zona(previo)
    assert llamadas[1][1] is None


def test_un_fallo_del_paso_no_corta_el_ciclo(db_session, salutem, ritmo, monkeypatch):
    def falla(db, ahora, desde):
        raise RuntimeError("boom")

    monkeypatch.setattr(orquestador, "sincronizar_profesionales", falla)

    assert correr("caliente", db_session, salutem, ritmo, ahora=lambda: AHORA, habilitado=True, dueno="t") == 0
    ejecucion = db_session.scalars(select(SalutemSyncEjecucion).order_by(SalutemSyncEjecucion.id.desc())).first()
    assert ejecucion.estado == "con_errores"
    assert "profesionales: RuntimeError: boom" in ejecucion.error
