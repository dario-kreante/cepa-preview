from datetime import date, datetime, timedelta, timezone

from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.services.salutem_sync.barrido import barrer_dia
from app.services.salutem_sync.incremental import ventana_caliente, ventana_fria, ventana_tibia
from tests.salutem_sync.conftest import AHORA

HOY = date(2026, 9, 16)
DIA = timedelta(days=1)
CITA = int(TipoFechaCita.FECHA_CITA)
CREACION = int(TipoFechaCita.FECHA_CREACION)


def _pares(salutem) -> set[tuple[date, int]]:
    return {(ll[1], ll[3]) for ll in salutem.llamadas_a("listar_citas")}


def test_caliente_al_mediodia_barre_creacion_de_hoy_y_citas_de_hoy_y_manana(db_session, salutem, ritmo):
    ventana_caliente(db_session, salutem, ritmo, AHORA)
    assert _pares(salutem) == {(HOY, CREACION), (HOY, CITA), (HOY + DIA, CITA)}


def test_caliente_pasada_la_medianoche_incluye_la_creacion_de_ayer(db_session, salutem, ritmo):
    medianoche_y_media = datetime(2026, 9, 16, 3, 30, tzinfo=timezone.utc)  # 00:30 en Santiago
    ventana_caliente(db_session, salutem, ritmo, medianoche_y_media)
    assert (HOY - DIA, CREACION) in _pares(salutem)


def test_caliente_detecta_una_cita_creada_hoy_para_otro_dia(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY + 3 * DIA, EstadoCitaSalutem.AGENDADO, creada="2026-09-16 11:40")

    r = ventana_caliente(db_session, salutem, ritmo, AHORA)

    assert r.contadores.nuevos >= 1
    assert db_session.get(SalutemCita, 9001) is not None


def test_tibia_refresca_una_atencion_editada_hace_tres_dias(db_session, salutem, ritmo):
    salutem.agregar_persona(501)
    salutem.agregar_cita(9001, 501, HOY - 3 * DIA)
    salutem.agregar_atencion(9001, anamnesis="inicial")
    barrer_dia(db_session, salutem, ritmo, HOY - 3 * DIA, TipoFechaCita.FECHA_CITA, AHORA)
    salutem.atenciones[9001]["anamnesis"] = "editada"

    r = ventana_tibia(db_session, salutem, ritmo, AHORA)

    assert r.contadores.cambiados == 1
    assert db_session.get(SalutemAtencion, 9001).contenido["anamnesis"] == "editada"
    assert {d for d, t in _pares(salutem) if t == CITA} >= {HOY - 7 * DIA, HOY + 30 * DIA}


def test_fria_cubre_noventa_dias_atras_y_ciento_ochenta_adelante(db_session, salutem, ritmo):
    avisos = []
    ventana_fria(db_session, salutem, ritmo, AHORA, al_terminar_dia=lambda: avisos.append(1))

    dias = {d for d, t in _pares(salutem) if t == CITA}
    assert min(dias) == HOY - 90 * DIA
    assert max(dias) == HOY + 180 * DIA
    assert len(dias) == 271
    assert len(avisos) == 271


def test_un_dia_con_error_queda_en_los_errores_de_la_ventana(db_session, salutem, ritmo):
    salutem.dias_con_error.add((HOY, int(EstadoCitaSalutem.ATENDIDO)))
    r = ventana_caliente(db_session, salutem, ritmo, AHORA)
    assert r.errores
