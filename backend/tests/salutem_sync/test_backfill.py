from datetime import date, timedelta

import pytest

from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.models.salutem_sync import SalutemSyncDia
from app.services.salutem_sync.backfill import (
    DIAS_FALLIDOS_PARA_ABORTAR,
    BackfillAbortadoError,
    ejecutar_backfill,
)
from tests.salutem_sync.conftest import AHORA

HOY = date(2026, 9, 16)
DIA = timedelta(days=1)


def _dias_barridos_por_cita(salutem) -> set[date]:
    return {ll[1] for ll in salutem.llamadas_a("listar_citas") if ll[3] == int(TipoFechaCita.FECHA_CITA)}


def test_recorre_hacia_atras_y_para_tras_n_dias_vacios(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - 2 * DIA, EstadoCitaSalutem.AGENDADO)
    salutem.agregar_cita(9002, 501, HOY - 5 * DIA, EstadoCitaSalutem.AGENDADO)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        dias_vacios_para_parar=3, dias_futuro=0, verificar=False,
    )

    assert r.primer_dia_con_datos == HOY - 5 * DIA
    assert r.dias_barridos == 9  # de HOY a HOY-8
    assert _dias_barridos_por_cita(salutem) == {HOY - i * DIA for i in range(9)}
    assert db_session.get(SalutemCita, 9002) is not None


def test_respeta_la_fecha_desde(db_session, salutem, ritmo):
    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - DIA, dias_futuro=0, verificar=False,
    )
    assert r.dias_barridos == 2


def test_se_reanuda_sin_repetir_dias_completos(db_session, salutem, ritmo):
    opciones = dict(hoy=HOY, ahora=AHORA, desde=HOY - 3 * DIA, dias_futuro=0, verificar=False)
    ejecutar_backfill(db_session, salutem, ritmo, **opciones)
    salutem.llamadas.clear()

    ejecutar_backfill(db_session, salutem, ritmo, **opciones)

    # Hoy nunca queda registrado (sigue cambiando); los días pasados sí.
    assert _dias_barridos_por_cita(salutem) == {HOY}
    assert db_session.get(SalutemSyncDia, (HOY, int(TipoFechaCita.FECHA_CITA))) is None
    assert db_session.get(SalutemSyncDia, (HOY - DIA, int(TipoFechaCita.FECHA_CITA))) is not None


def test_un_dia_con_error_no_queda_registrado(db_session, salutem, ritmo):
    salutem.dias_con_error.add((HOY - DIA, int(EstadoCitaSalutem.ATENDIDO)))

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - 2 * DIA, dias_futuro=0, verificar=False,
    )

    assert r.dias_con_error == 1
    assert r.errores
    assert db_session.get(SalutemSyncDia, (HOY - DIA, int(TipoFechaCita.FECHA_CITA))) is None
    assert db_session.get(SalutemSyncDia, (HOY - 2 * DIA, int(TipoFechaCita.FECHA_CITA))) is not None


def test_trae_las_citas_futuras(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9100, 501, HOY + 10 * DIA, EstadoCitaSalutem.AGENDADO)

    ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY, dias_futuro=15, verificar=False,
    )

    assert db_session.get(SalutemCita, 9100) is not None


def test_la_verificacion_recupera_atenciones_que_el_barrido_no_vio(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9001)
    # Atención antigua, fuera del rango barrido.
    salutem.agregar_cita(9200, 501, HOY - 400 * DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9200)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - 2 * DIA, dias_futuro=0, verificar=True,
    )

    assert r.atenciones_recuperadas == 1
    assert r.atenciones_anteriores == 1
    assert db_session.get(SalutemAtencion, 9200) is not None


def test_avisa_atenciones_anteriores_aunque_el_rango_barrido_no_tenga_citas(db_session, salutem, ritmo):
    # Visto en QA: SALUTEM tenía datos hasta enero y el rango barrido estaba vacío.
    salutem.agregar_persona(501)
    salutem.agregar_cita(9200, 501, HOY - 400 * DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9200)
    # La persona entra a la copia por una cita futura, como en un backfill real.
    salutem.agregar_cita(9300, 501, HOY + DIA, EstadoCitaSalutem.AGENDADO)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - 2 * DIA, dias_futuro=1, verificar=True,
    )

    assert r.primer_dia_con_datos is None
    assert r.primer_dia_barrido == HOY - 2 * DIA
    assert r.atenciones_anteriores == 1


def test_dias_fallidos_no_se_confunden_con_vacios_y_abortan(db_session, salutem, ritmo):
    """Si SALUTEM rechaza todos los días pasados, el backfill no debe gastar miles de
    llamadas creyendo que son días vacíos: debe abortar tras DIAS_FALLIDOS_PARA_ABORTAR
    días fallidos seguidos, sin llegar nunca a `dias_vacios_para_parar`."""
    for i in range(20):
        dia = HOY - i * DIA
        for estado in EstadoCitaSalutem:
            salutem.dias_con_error.add((dia, int(estado)))

    with pytest.raises(BackfillAbortadoError):
        ejecutar_backfill(
            db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
            dias_vacios_para_parar=3, dias_futuro=0, verificar=False,
        )

    # No se detuvo por días vacíos (habría bastado con 3 días): abortó tras los fallidos.
    assert len(_dias_barridos_por_cita(salutem)) == DIAS_FALLIDOS_PARA_ABORTAR


def test_dia_fallido_entre_dias_con_datos_no_cuenta_como_vacio(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - DIA, EstadoCitaSalutem.AGENDADO)
    salutem.agregar_cita(9002, 501, HOY - 3 * DIA, EstadoCitaSalutem.AGENDADO)
    for estado in EstadoCitaSalutem:
        salutem.dias_con_error.add((HOY - 2 * DIA, int(estado)))

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        dias_vacios_para_parar=2, dias_futuro=0, verificar=False,
    )

    assert r.primer_dia_con_datos == HOY - 3 * DIA


def test_avisa_al_terminar_cada_dia(db_session, salutem, ritmo):
    avisos = []
    ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - DIA, dias_futuro=2, verificar=False,
        al_terminar_dia=lambda: avisos.append(1),
    )
    assert len(avisos) == 4  # 2 futuros + hoy + ayer


def test_la_verificacion_sigue_tras_registros_rechazados(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_persona(502, "11111111-1")
    salutem.agregar_cita(9001, 501, HOY, EstadoCitaSalutem.AGENDADO)
    salutem.agregar_cita(9002, 502, HOY, EstadoCitaSalutem.AGENDADO)
    # Atenciones que el barrido no ve (la cita no está Atendida): solo las trae la verificación.
    salutem.agregar_cita(9100, 501, HOY - 400 * DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9100)
    salutem.agregar_cita(9101, 501, HOY - 401 * DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9101)
    salutem.agregar_cita(9200, 502, HOY - 400 * DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9200)
    salutem.citas_con_error.add(9100)
    ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY, dias_futuro=0, verificar=False,
    )

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY, dias_futuro=0, verificar=True,
    )

    assert "cita 9100: ERROR_RARO" in r.errores
    assert db_session.get(SalutemAtencion, 9101) is not None
    assert db_session.get(SalutemAtencion, 9200) is not None


def test_la_verificacion_sigue_si_se_rechaza_el_listado_de_una_persona(
    db_session, salutem, ritmo, monkeypatch
):
    from app.integrations.salutem.errors import SalutemError

    salutem.agregar_persona(501)
    salutem.agregar_persona(502, "11111111-1")
    salutem.agregar_cita(9001, 501, HOY, EstadoCitaSalutem.AGENDADO)
    salutem.agregar_cita(9002, 502, HOY, EstadoCitaSalutem.AGENDADO)
    salutem.agregar_cita(9200, 502, HOY - 400 * DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9200)
    original = salutem.listar_atenciones

    def listar(salutem_id):
        if salutem_id == 501:
            raise SalutemError("raro", codigo="ERROR_RARO")
        return original(salutem_id)

    monkeypatch.setattr(salutem, "listar_atenciones", listar)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY, dias_futuro=0, verificar=True,
    )

    assert "persona 501: ERROR_RARO" in r.errores
    assert db_session.get(SalutemAtencion, 9200) is not None


def test_un_dia_con_salutem_caido_no_mata_la_carga_inicial(db_session, salutem, ritmo):
    """Visto en la VM el 2026-09-17: tras 8 h y 38.420 llamadas, un HTTP 504 de SALUTEM
    abortó el backfill entero. Un día caído se trata como día fallido y se sigue."""
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - 2 * DIA, EstadoCitaSalutem.AGENDADO)
    salutem.dias_caidos.add(HOY - DIA)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - 3 * DIA, dias_futuro=0, verificar=False,
    )

    assert r.dias_con_error == 1
    assert any("504" in e for e in r.errores)
    # El día caído no queda registrado (se reintenta), los demás sí.
    assert db_session.get(SalutemSyncDia, (HOY - DIA, int(TipoFechaCita.FECHA_CITA))) is None
    assert db_session.get(SalutemSyncDia, (HOY - 2 * DIA, int(TipoFechaCita.FECHA_CITA))) is not None
    assert db_session.get(SalutemCita, 9001) is not None


def test_salutem_caido_muchos_dias_seguidos_aborta(db_session, salutem, ritmo):
    for i in range(20):
        salutem.dias_caidos.add(HOY - i * DIA)

    with pytest.raises(BackfillAbortadoError):
        ejecutar_backfill(
            db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
            dias_vacios_para_parar=365, dias_futuro=0, verificar=False,
        )


def test_la_verificacion_sigue_si_una_persona_falla_por_caida(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_persona(502, "11111111-1")
    salutem.agregar_cita(9001, 501, HOY - DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9001)
    salutem.agregar_cita(9002, 502, HOY - DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9002)
    salutem.personas_caidas.add(501)

    r = ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - DIA, dias_futuro=0, verificar=True,
    )

    assert any("persona 501" in e and "504" in e for e in r.errores)
    assert db_session.get(SalutemAtencion, 9002) is not None
