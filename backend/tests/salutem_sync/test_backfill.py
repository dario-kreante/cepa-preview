from datetime import date, timedelta

from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.models.salutem_sync import SalutemSyncDia
from app.services.salutem_sync.backfill import ejecutar_backfill
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


def test_avisa_al_terminar_cada_dia(db_session, salutem, ritmo):
    avisos = []
    ejecutar_backfill(
        db_session, salutem, ritmo, hoy=HOY, ahora=AHORA,
        desde=HOY - DIA, dias_futuro=2, verificar=False,
        al_terminar_dia=lambda: avisos.append(1),
    )
    assert len(avisos) == 4  # 2 futuros + hoy + ayer
