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


def test_caliente_al_mediodia_barre_creacion_de_hoy_y_citas_de_siete_dias_atras_a_catorce_adelante(
    db_session, salutem, ritmo
):
    ventana_caliente(db_session, salutem, ritmo, AHORA)
    citas = {(HOY + i * DIA, CITA) for i in range(-7, 15)}
    assert _pares(salutem) == {(HOY, CREACION)} | citas


def test_caliente_ve_el_cambio_de_estado_de_una_cita_de_la_semana_pasada(db_session, salutem, ritmo):
    # Lo que el CEPA hace en SALUTEM debe verse en SIGE en 5 minutos (QA UTalca 29-10, QA-005).
    salutem.agregar_persona(501)
    salutem.agregar_cita(9002, 501, HOY - 7 * DIA, EstadoCitaSalutem.AGENDADO)
    barrer_dia(db_session, salutem, ritmo, HOY - 7 * DIA, TipoFechaCita.FECHA_CITA, AHORA)
    salutem.citas[9002]["estadoCitaId"] = int(EstadoCitaSalutem.ANULADO)

    ventana_caliente(db_session, salutem, ritmo, AHORA)

    assert db_session.get(SalutemCita, 9002).estado_id == int(EstadoCitaSalutem.ANULADO)


def test_caliente_no_barre_fuera_de_la_ventana(db_session, salutem, ritmo):
    ventana_caliente(db_session, salutem, ritmo, AHORA)
    pares = _pares(salutem)
    assert (HOY - 8 * DIA, CITA) not in pares
    assert (HOY + 15 * DIA, CITA) not in pares


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


def test_caliente_tras_el_salto_de_horario_incluye_la_creacion_de_ayer(db_session, salutem, ritmo):
    # 2026-09-06 en Chile: 24:00 pasa a 01:00. 04:30 UTC = 01:30 local, 30 min reales después de medianoche.
    tras_el_salto = datetime(2026, 9, 6, 4, 30, tzinfo=timezone.utc)
    ventana_caliente(db_session, salutem, ritmo, tras_el_salto)
    assert (date(2026, 9, 5), CREACION) in _pares(salutem)


def _atencion_copiada(db, salutem, ritmo, cita_id, dia, especialidad):
    salutem.agregar_persona(501)
    salutem.agregar_cita(cita_id, 501, dia)
    salutem.agregar_atencion(cita_id, anamnesis="inicial", especialidadNombre=especialidad)
    barrer_dia(db, salutem, ritmo, dia, TipoFechaCita.FECHA_CITA, AHORA)


def _releidas(salutem) -> set[int]:
    return {ll[2] for ll in salutem.llamadas_a("obtener_atencion")}


def test_caliente_relee_el_control_medico_de_ayer_editado(db_session, salutem, ritmo):
    """El médico suele completar la licencia o la receta al día siguiente: la alerta no
    puede esperar a la tibia de la hora siguiente."""
    _atencion_copiada(db_session, salutem, ritmo, 9101, HOY - DIA, "Médico/a")
    salutem.atenciones[9101]["anamnesis"] = "editada"
    salutem.llamadas.clear()

    r = ventana_caliente(db_session, salutem, ritmo, AHORA)

    assert r.contadores.cambiados == 1
    assert db_session.get(SalutemAtencion, 9101).contenido["anamnesis"] == "editada"


def test_caliente_no_relee_otras_especialidades_ni_controles_antiguos(db_session, salutem, ritmo):
    _atencion_copiada(db_session, salutem, ritmo, 9102, HOY - DIA, "Contención Psicologíca")
    _atencion_copiada(db_session, salutem, ritmo, 9103, HOY - 3 * DIA, "Médico/a")
    salutem.llamadas.clear()

    ventana_caliente(db_session, salutem, ritmo, AHORA)

    assert _releidas(salutem).isdisjoint({9102, 9103})


def test_caliente_copia_a_las_personas_creadas_hoy_aunque_no_tengan_citas(db_session, salutem, ritmo):
    from app.models.salutem_copia import SalutemPersona

    salutem.agregar_persona(4061957, rut="sin_id_2817285", fechaCreacion="2026-09-16 11:40")
    salutem.agregar_persona(4061958, rut="sin_id_2817286", fechaCreacion="2026-09-10 11:40")

    ventana_caliente(db_session, salutem, ritmo, AHORA)

    assert ("listar_personas", HOY) in salutem.llamadas
    assert db_session.get(SalutemPersona, 4061957) is not None
    assert db_session.get(SalutemPersona, 4061958) is None  # creada otro día


def test_tibia_recupera_las_personas_creadas_en_la_ultima_semana(db_session, salutem, ritmo):
    from app.models.salutem_copia import SalutemPersona

    salutem.agregar_persona(4061959, rut="sin_id_2817287", fechaCreacion="2026-09-10 08:00")

    ventana_tibia(db_session, salutem, ritmo, AHORA)

    assert db_session.get(SalutemPersona, 4061959) is not None
