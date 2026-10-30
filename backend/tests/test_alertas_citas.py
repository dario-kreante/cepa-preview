"""Alertas de control médico (sin falsas alarmas) e inasistencia desde SALUTEM."""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import select

from app.domain.enums import EstadoCaso
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.alertas import AlertaNotif
from app.models.cita import Cita
from app.models.config_alerta import ConfigAlerta
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemCita, SalutemPersona
from app.services.alertas import ejecutar_job_alertas
from app.services.alertas_citas import (
    CASO_TIPO_INASISTENCIA,
    alertar_inasistencia,
    alertar_posible_encuadre,
    resolver_alertas_con_hora,
)
from app.services.config_alertas import cargar_ventanas

HOY = date(2026, 10, 16)
AHORA = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
_seq = {"n": 0}


def _n() -> int:
    _seq["n"] += 1
    return _seq["n"]


def _paciente(db, rut: str) -> Paciente:
    p = Paciente(rut=rut, nombre="Paciente Alerta", sexo="F", edad=40, region="Maule")
    db.add(p)
    db.flush()
    return p


def _ingreso(db, paciente: Paciente, estado: str = EstadoCaso.ACTIVO.value) -> Ingreso:
    i = Ingreso(
        paciente_id=paciente.id, folio=f"F-ALC-{_n()}", folio_manual=True,
        fecha_ingreso=date(2026, 1, 1), tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="test", estado=estado,
    )
    db.add(i)
    db.flush()
    return i


def _control(
    db, ingreso, *, origen="SALUTEM", agendado=False, proximo=None, fecha=date(2026, 10, 1)
) -> ControlMedico:
    c = ControlMedico(
        ingreso_id=ingreso.id, fecha_control=fecha, semana_control=1,
        medico_tratante="Dra Alerta", region_derivacion="Maule",
        proximo_control=proximo or HOY + timedelta(days=3),
        proximo_agendado=agendado, tiene_licencia=False, origen=origen,
    )
    db.add(c)
    db.flush()
    return c


def _hora_vigente(db, rut: str, persona_id: int) -> None:
    db.add(
        SalutemPersona(
            salutem_id=persona_id, rut=rut, contenido={}, hash_contenido="h",
            visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
        )
    )
    db.flush()
    db.add(
        SalutemCita(
            cita_id=_n() + 910000, persona_id=persona_id, fecha_cita=HOY + timedelta(days=2),
            estado_id=int(EstadoCitaSalutem.AGENDADO), contenido={}, hash_contenido="h",
            visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
        )
    )
    db.flush()


def _alertas(db, tipo: str, caso_id: int | None = None) -> list[AlertaNotif]:
    q = select(AlertaNotif).where(AlertaNotif.tipo == tipo)
    if caso_id is not None:
        q = q.where(AlertaNotif.caso_id == caso_id)
    return list(db.scalars(q))


def _cita_inasistencia(db, ingreso, *, dias_atras=2, sid=None, especialidad="Médico/a") -> Cita:
    c = Cita(
        ingreso_id=ingreso.id, estado="inasistencia", fecha=HOY - timedelta(days=dias_atras),
        salutem_cita_id=sid or _n() + 920000, origen="SALUTEM", especialidad=especialidad,
    )
    db.add(c)
    db.flush()
    return c


def _alertar(db, cita: Cita) -> bool:
    return alertar_inasistencia(
        db, salutem_cita_id=cita.salutem_cita_id, cita=cita, hoy=HOY, ventanas=cargar_ventanas(db)
    )


# ── Control médico ─────────────────────────────────────────────────────────────


def test_control_salutem_con_hora_vigente_no_alerta(db_session):
    p = _paciente(db_session, "10000001")
    c = _control(db_session, _ingreso(db_session, p))
    _hora_vigente(db_session, "10000001", 9101)
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    assert _alertas(db_session, "control_medico", c.id) == []


def test_control_salutem_proximo_agendado_sin_hora_si_alerta(db_session):
    p = _paciente(db_session, "10000002")
    c = _control(db_session, _ingreso(db_session, p), origen="SALUTEM", agendado=True)
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    assert len(_alertas(db_session, "control_medico", c.id)) == 1


def test_control_cepa_proximo_agendado_no_alerta(db_session):
    p = _paciente(db_session, "10000003")
    c = _control(db_session, _ingreso(db_session, p), origen="CEPA", agendado=True)
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    assert _alertas(db_session, "control_medico", c.id) == []


def test_control_de_ingreso_cerrado_no_alerta(db_session):
    p = _paciente(db_session, "10000004")
    c = _control(db_session, _ingreso(db_session, p, estado=EstadoCaso.CERRADO.value))
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    assert _alertas(db_session, "control_medico", c.id) == []


def test_alerta_control_abierta_se_resuelve_al_aparecer_hora(db_session):
    p = _paciente(db_session, "10000005")
    c = _control(db_session, _ingreso(db_session, p))
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    assert len(_alertas(db_session, "control_medico", c.id)) == 1
    _hora_vigente(db_session, "10000005", 9105)
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    (alerta,) = _alertas(db_session, "control_medico", c.id)
    assert alerta.estado == EstadoAlerta.RESUELTA.value
    assert alerta.resuelta_en is not None


def test_ultimo_control_cepa_agendado_con_anterior_sin_agendar_no_alerta(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000006"))
    anterior = _control(db_session, ing, origen="CEPA", agendado=False, fecha=date(2026, 9, 20))
    ultimo = _control(db_session, ing, origen="CEPA", agendado=True, fecha=date(2026, 10, 1))
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    assert _alertas(db_session, "control_medico", ultimo.id) == []
    assert _alertas(db_session, "control_medico", anterior.id) == []


def test_control_desempata_por_fecha_y_luego_por_id(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000007"))
    viejo = _control(db_session, ing, fecha=date(2026, 9, 1))
    nuevo = _control(db_session, ing, fecha=date(2026, 10, 1))
    mismo_dia = _control(db_session, ing, fecha=date(2026, 10, 1))  # id mayor, misma fecha
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    assert _alertas(db_session, "control_medico", viejo.id) == []
    assert _alertas(db_session, "control_medico", nuevo.id) == []
    assert len(_alertas(db_session, "control_medico", mismo_dia.id)) == 1


def test_job_sin_hitos_nuevos_persiste_las_resoluciones(db_session):
    p = _paciente(db_session, "10000008")
    c = _control(db_session, _ingreso(db_session, p))
    ejecutar_job_alertas(db_session, actor="test", hoy=HOY)
    (alerta,) = _alertas(db_session, "control_medico", c.id)
    _hora_vigente(db_session, "10000008", 9108)
    db_session.commit()  # el estado previo queda firme; lo que sigue debe commitearlo el job

    assert ejecutar_job_alertas(db_session, actor="test", hoy=HOY) == 0
    db_session.rollback()  # si el job solo hubiera flusheado, la resolución se perdería aquí

    db_session.refresh(alerta)
    assert alerta.estado == EstadoAlerta.RESUELTA.value


# ── Inasistencia ───────────────────────────────────────────────────────────────


def test_inasistencia_reciente_crea_alerta(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000011"))
    cita = _cita_inasistencia(db_session, ing)
    assert _alertar(db_session, cita) is True
    (a,) = _alertas(db_session, TipoAlerta.INASISTENCIA.value)
    assert (a.caso_tipo, a.caso_id) == (CASO_TIPO_INASISTENCIA, cita.salutem_cita_id)
    assert CASO_TIPO_INASISTENCIA == "salutem_cita"
    assert a.estado == EstadoAlerta.PENDIENTE.value
    assert a.plazo_objetivo.astimezone(timezone.utc).date() == cita.fecha


def test_inasistencia_antigua_no_alerta(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000012"))
    cita = _cita_inasistencia(db_session, ing, dias_atras=15)
    assert _alertar(db_session, cita) is False
    assert _alertas(db_session, TipoAlerta.INASISTENCIA.value) == []


def test_inasistencia_no_se_duplica_en_segunda_corrida(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000013"))
    cita = _cita_inasistencia(db_session, ing)
    assert _alertar(db_session, cita) is True
    assert _alertar(db_session, cita) is False
    assert len(_alertas(db_session, TipoAlerta.INASISTENCIA.value, cita.salutem_cita_id)) == 1


def test_inasistencia_no_se_repite_tras_resolverla(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000014"))
    cita = _cita_inasistencia(db_session, ing)
    _alertar(db_session, cita)
    (a,) = _alertas(db_session, TipoAlerta.INASISTENCIA.value)
    a.estado = EstadoAlerta.RESUELTA.value
    db_session.flush()
    assert _alertar(db_session, cita) is False
    assert len(_alertas(db_session, TipoAlerta.INASISTENCIA.value, cita.salutem_cita_id)) == 1


def test_inasistencia_tipo_desactivado_no_alerta(db_session):
    fila = db_session.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == "inasistencia"))
    fila.activo = False
    db_session.flush()
    ing = _ingreso(db_session, _paciente(db_session, "10000015"))
    cita = _cita_inasistencia(db_session, ing)
    assert _alertar(db_session, cita) is False


def test_inasistencia_especialidad_fuera_de_filtro_no_alerta(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.alertas_citas.get_settings",
        lambda: SimpleNamespace(citas_especialidades_reportes_set=frozenset({"psicología"})),
    )
    ing = _ingreso(db_session, _paciente(db_session, "10000016"))
    fuera = _cita_inasistencia(db_session, ing, especialidad="Médico/a")
    dentro = _cita_inasistencia(db_session, ing, especialidad="Psicología")
    assert _alertar(db_session, fuera) is False
    assert _alertar(db_session, dentro) is True


def test_inasistencia_se_resuelve_al_aparecer_hora(db_session):
    p = _paciente(db_session, "10000017")
    cita = _cita_inasistencia(db_session, _ingreso(db_session, p))
    _alertar(db_session, cita)
    assert resolver_alertas_con_hora(db_session, HOY, "test") == 0
    _hora_vigente(db_session, "10000017", 9117)
    assert resolver_alertas_con_hora(db_session, HOY, "test") == 1
    (a,) = _alertas(db_session, TipoAlerta.INASISTENCIA.value)
    assert a.estado == EstadoAlerta.RESUELTA.value
    assert resolver_alertas_con_hora(db_session, HOY, "test") == 0


def test_inasistencia_sin_cita_queda_abierta(db_session):
    p = _paciente(db_session, "10000018")
    ing = _ingreso(db_session, p)
    cita = _cita_inasistencia(db_session, ing)
    _alertar(db_session, cita)
    db_session.delete(cita)
    db_session.flush()
    _hora_vigente(db_session, "10000018", 9118)
    assert resolver_alertas_con_hora(db_session, HOY, "test") == 0
    (a,) = _alertas(db_session, TipoAlerta.INASISTENCIA.value)
    assert a.estado == EstadoAlerta.PENDIENTE.value


def test_sync_de_citas_crea_alerta_de_inasistencia(db_session):
    from app.services.salutem_sync.citas_cepa import sincronizar_citas

    p = _paciente(db_session, "10000019")
    _ingreso(db_session, p)
    db_session.add(
        SalutemPersona(
            salutem_id=9119, rut="10000019", contenido={}, hash_contenido="h",
            visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
        )
    )
    db_session.flush()
    sid = _n() + 930000
    db_session.add(
        SalutemCita(
            cita_id=sid, persona_id=9119, fecha_cita=HOY - timedelta(days=2),
            estado_id=int(EstadoCitaSalutem.NO_ASISTE), contenido={}, hash_contenido="h",
            visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
        )
    )
    db_session.flush()
    r = sincronizar_citas(db_session, desde=None, ahora=AHORA)
    assert r.alertas_inasistencia == 1
    assert len(_alertas(db_session, TipoAlerta.INASISTENCIA.value, sid)) == 1
    assert sincronizar_citas(db_session, desde=None, ahora=AHORA).alertas_inasistencia == 0


def test_alerta_de_inasistencia_fallida_no_bloquea_las_demas(db_session, monkeypatch):
    from app.services.salutem_sync import citas_cepa

    p = _paciente(db_session, "10000020")
    _ingreso(db_session, p)
    db_session.add(
        SalutemPersona(
            salutem_id=9120, rut="10000020", contenido={}, hash_contenido="h",
            visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
        )
    )
    db_session.flush()
    for dias in (2, 3):
        db_session.add(
            SalutemCita(
                cita_id=_n() + 940000, persona_id=9120, fecha_cita=HOY - timedelta(days=dias),
                estado_id=int(EstadoCitaSalutem.NO_ASISTE), contenido={}, hash_contenido="h",
                visto_primera_vez=AHORA, visto_ultima_vez=AHORA, cambiado_en=AHORA,
            )
        )
    db_session.flush()

    real = citas_cepa.alertar_inasistencia
    llamadas = []

    def falla_la_primera(db, **kw):
        llamadas.append(kw["salutem_cita_id"])
        if len(llamadas) == 1:
            raise RuntimeError("boom")
        return real(db, **kw)

    monkeypatch.setattr(citas_cepa, "alertar_inasistencia", falla_la_primera)

    r = citas_cepa.sincronizar_citas(db_session, desde=None, ahora=AHORA)

    assert len(llamadas) == 2
    assert r.alertas_inasistencia == 1
    assert len(r.errores) == 1 and "boom" in r.errores[0]
    assert len(_alertas(db_session, TipoAlerta.INASISTENCIA.value)) == 1


# ── Posible encuadre (reunión 29-10, D6) ──────────────────────────────────────


def _encuadre(db, cita: Cita) -> bool:
    return alertar_posible_encuadre(
        db, salutem_cita_id=cita.salutem_cita_id, cita=cita, hoy=HOY, ventanas=cargar_ventanas(db)
    )


def test_la_primera_inasistencia_no_alerta_encuadre(db_session):
    ing = _ingreso(db_session, _paciente(db_session, "10000031"))
    assert _encuadre(db_session, _cita_inasistencia(db_session, ing)) is False
    assert _alertas(db_session, TipoAlerta.POSIBLE_ENCUADRE.value) == []


def test_la_segunda_inasistencia_alerta_y_cada_nueva_vuelve_a_alertar(db_session):
    paciente = _paciente(db_session, "10000032")
    # El histórico cuenta aunque sea de otro ingreso o muy antiguo.
    _cita_inasistencia(db_session, _ingreso(db_session, paciente), dias_atras=400)
    ing = _ingreso(db_session, paciente, estado=EstadoCaso.ENCUADRE.value)
    segunda = _cita_inasistencia(db_session, ing, dias_atras=3)
    tercera = _cita_inasistencia(db_session, ing, dias_atras=1)

    assert _encuadre(db_session, segunda) is True
    assert _encuadre(db_session, tercera) is True
    assert _encuadre(db_session, tercera) is False  # no se duplica
    alertas = _alertas(db_session, TipoAlerta.POSIBLE_ENCUADRE.value)
    assert sorted(a.caso_id for a in alertas) == sorted([segunda.salutem_cita_id, tercera.salutem_cita_id])
    assert all(a.caso_tipo == CASO_TIPO_INASISTENCIA for a in alertas)


def test_la_alerta_de_encuadre_se_apaga_en_la_configuracion(db_session):
    fila = db_session.scalar(select(ConfigAlerta).where(ConfigAlerta.tipo == "posible_encuadre"))
    fila.activo = False
    db_session.flush()
    ing = _ingreso(db_session, _paciente(db_session, "10000033"))
    _cita_inasistencia(db_session, ing, dias_atras=5)
    assert _encuadre(db_session, _cita_inasistencia(db_session, ing)) is False


def test_la_alerta_de_encuadre_no_se_resuelve_por_tener_hora(db_session):
    paciente = _paciente(db_session, "10000034")
    ing = _ingreso(db_session, paciente)
    _cita_inasistencia(db_session, ing, dias_atras=5)
    _encuadre(db_session, _cita_inasistencia(db_session, ing))
    _hora_vigente(db_session, "10000034", 777034)
    paciente.salutem_persona_id = 777034
    db_session.flush()
    resolver_alertas_con_hora(db_session, HOY, "test")
    (a,) = _alertas(db_session, TipoAlerta.POSIBLE_ENCUADRE.value)
    assert a.estado == EstadoAlerta.PENDIENTE.value
