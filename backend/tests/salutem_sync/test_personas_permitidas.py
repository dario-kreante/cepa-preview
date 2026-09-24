"""Lista de personas permitidas: el sync solo copia a las personas autorizadas.

SALUTEM QA trae identidades reales. Mientras se valida con los pacientes de prueba,
el sync tiene que poder limitarse a ellos sin salir a buscar a nadie más.
"""

from datetime import date

from app.config import Settings
from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.services.salutem_sync.barrido import barrer_dia
from app.services.salutem_sync.filtro import ClientePersonasPermitidas, envolver_si_corresponde
from tests.salutem_sync.conftest import AHORA

DIA = date(2025, 1, 22)
PRUEBA = 501
REAL = 777


def _con_dos_personas(salutem):
    salutem.agregar_persona(PRUEBA, "sin_id_1", tipoIdentificacion="SIN IDENTIFICACION")
    salutem.agregar_persona(REAL, "12345678-5")
    salutem.agregar_cita(9001, PRUEBA, DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9001, anamnesis="de prueba")
    salutem.agregar_cita(9002, REAL, DIA, EstadoCitaSalutem.ATENDIDO)
    salutem.agregar_atencion(9002, anamnesis="real")
    return salutem


def test_la_lista_viene_vacia_y_se_parsea_como_ids():
    assert Settings(_env_file=None).salutem_sync_personas_permitidas_ids == frozenset()
    s = Settings(_env_file=None, salutem_sync_personas_permitidas=" 1332404, 1216017 ,")
    assert s.salutem_sync_personas_permitidas_ids == frozenset({1332404, 1216017})


def test_el_barrido_solo_copia_a_las_personas_permitidas(db_session, salutem, ritmo):
    cliente = ClientePersonasPermitidas(_con_dos_personas(salutem), frozenset({PRUEBA}))

    r = barrer_dia(db_session, cliente, ritmo, DIA, TipoFechaCita.FECHA_CITA, AHORA)

    assert r.citas == 1
    assert db_session.get(SalutemPersona, PRUEBA) is not None
    assert db_session.get(SalutemAtencion, 9001) is not None
    assert db_session.get(SalutemPersona, REAL) is None
    assert db_session.get(SalutemCita, 9002) is None
    assert db_session.get(SalutemAtencion, 9002) is None
    # Nunca se le pide a SALUTEM nada de la persona no permitida.
    assert (("obtener_persona", REAL)) not in salutem.llamadas
    assert not [ll for ll in salutem.llamadas_a("obtener_atencion") if ll[1] == REAL]


def test_no_pide_personas_ni_atenciones_fuera_de_la_lista(salutem):
    cliente = ClientePersonasPermitidas(_con_dos_personas(salutem), frozenset({PRUEBA}))

    assert cliente.obtener_persona(REAL) is None
    assert cliente.obtener_atencion(REAL, 9002) is None
    assert cliente.listar_atenciones(REAL) == []
    assert cliente.resolver_persona("12345678-5") is None
    assert salutem.llamadas_a("obtener_persona") == []
    assert salutem.llamadas_a("obtener_atencion") == []
    assert salutem.llamadas_a("listar_atenciones") == []

    assert cliente.obtener_persona(PRUEBA) is not None
    assert cliente.obtener_atencion(PRUEBA, 9001) is not None


def test_sin_lista_el_cliente_queda_tal_cual(salutem):
    assert envolver_si_corresponde(salutem, frozenset()) is salutem
    assert isinstance(envolver_si_corresponde(salutem, frozenset({PRUEBA})), ClientePersonasPermitidas)
