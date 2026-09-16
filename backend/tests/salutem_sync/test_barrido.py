from datetime import date, timedelta

import pytest

from app.integrations.salutem.errors import SalutemAuthError
from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.services.salutem_sync.barrido import barrer_dia, refrescar_atenciones
from tests.salutem_sync.conftest import AHORA

DIA = date(2025, 1, 22)
DESPUES = AHORA + timedelta(minutes=5)
POR_CITA = TipoFechaCita.FECHA_CITA


@pytest.fixture
def con_datos(salutem):
    salutem.agregar_persona(501, "12345678-5")
    salutem.agregar_cita(9001, 501, DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9001, anamnesis="inicial")
    salutem.agregar_cita(9002, 501, DIA, EstadoCitaSalutem.AGENDADO)
    return salutem


def test_primer_barrido_trae_citas_persona_y_atencion(db_session, con_datos, ritmo):
    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)

    assert r.completo
    assert r.citas == 2
    assert r.contadores.nuevos == 4  # 2 citas + 1 persona + 1 atención
    assert len(con_datos.llamadas_a("listar_citas")) == 9
    assert db_session.get(SalutemPersona, 501) is not None
    assert db_session.get(SalutemAtencion, 9001).contenido["anamnesis"] == "inicial"
    assert db_session.get(SalutemAtencion, 9002) is None


def test_segundo_barrido_sin_cambios_no_trae_nada_mas(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    con_datos.llamadas.clear()

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert (r.contadores.nuevos, r.contadores.cambiados, r.contadores.desaparecidos) == (0, 0, 0)
    assert con_datos.llamadas_a("obtener_atencion") == []
    assert con_datos.llamadas_a("obtener_persona") == []


def test_cita_que_pasa_a_atendida_trae_su_atencion(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    con_datos.citas[9002]["estadoCitaId"] = int(EstadoCitaSalutem.ATENDIDO)
    con_datos.agregar_atencion(9002, anamnesis="segunda")

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert r.contadores.cambiados == 1
    assert r.contadores.nuevos == 1
    assert db_session.get(SalutemAtencion, 9002) is not None


def test_cita_que_ya_no_aparece_queda_marcada(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    del con_datos.citas[9002]

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert r.contadores.desaparecidos == 1
    assert db_session.get(SalutemCita, 9002).desaparecida_en is not None


def test_un_estado_rechazado_no_marca_desaparecidas(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    del con_datos.citas[9002]
    con_datos.dias_con_error.add((DIA, int(EstadoCitaSalutem.AGENDADO)))

    r = barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, DESPUES)

    assert not r.completo
    assert r.errores
    assert r.contadores.desaparecidos == 0
    assert db_session.get(SalutemCita, 9002).desaparecida_en is None


def test_por_fecha_de_creacion_no_marca_desaparecidas(db_session, con_datos, ritmo):
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    del con_datos.citas[9002]

    r = barrer_dia(db_session, con_datos, ritmo, DIA, TipoFechaCita.FECHA_CREACION, DESPUES)

    assert r.contadores.desaparecidos == 0


def test_credencial_rechazada_se_propaga(db_session, con_datos, ritmo):
    con_datos.credencial_rechazada = True
    with pytest.raises(SalutemAuthError):
        barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)


def test_refrescar_detecta_ediciones_y_atenciones_borradas(db_session, con_datos, ritmo):
    con_datos.agregar_cita(9003, 501, DIA, EstadoCitaSalutem.ATENDIDO)
    con_datos.agregar_atencion(9003)
    barrer_dia(db_session, con_datos, ritmo, DIA, POR_CITA, AHORA)
    con_datos.atenciones[9001]["anamnesis"] = "editada"
    del con_datos.atenciones[9003]

    contadores = refrescar_atenciones(db_session, con_datos, ritmo, DIA, DIA, DESPUES)

    assert contadores.cambiados == 1
    assert contadores.desaparecidos == 1
    assert db_session.get(SalutemAtencion, 9001).contenido["anamnesis"] == "editada"
    assert db_session.get(SalutemAtencion, 9003).desaparecida_en is not None
