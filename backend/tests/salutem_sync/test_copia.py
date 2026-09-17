from datetime import date, timedelta

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, PersonaSalutem
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.services.salutem_sync import copia
from app.services.salutem_sync.tipos import Resultado
from tests.salutem_sync.conftest import AHORA

DIA = date(2025, 1, 22)
DESPUES = AHORA + timedelta(minutes=5)


def _cita(cita_id=9001, estado=3, fecha=DIA, **extra) -> CitaSalutem:
    return CitaSalutem.desde_api(
        {
            "personaId": 501,
            "citaId": cita_id,
            "citaFecha": fecha.isoformat(),
            "citaFechaCreacion": "2025-01-20 15:16",
            "estadoCitaId": estado,
            **extra,
        }
    )


def _atencion(cita_id=9001, anamnesis="inicial") -> AtencionSalutem:
    return AtencionSalutem.desde_api(
        {"personaId": 501, "citaId": cita_id, "citaFecha": DIA.isoformat(), "anamnesis": anamnesis}
    )


def test_cita_nueva_igual_y_cambiada(db_session):
    assert copia.guardar_cita(db_session, _cita(), AHORA) is Resultado.NUEVO
    assert copia.guardar_cita(db_session, _cita(), DESPUES) is Resultado.IGUAL
    assert copia.guardar_cita(db_session, _cita(estado=2), DESPUES) is Resultado.CAMBIADO

    fila = db_session.get(SalutemCita, 9001)
    assert fila.estado_id == 2
    assert fila.persona_id == 501
    assert fila.fecha_cita == DIA
    assert fila.fecha_creacion.strftime("%Y-%m-%d %H:%M") == "2025-01-20 15:16"
    assert fila.contenido["estadoCitaId"] == 2


def test_persona_guarda_el_rut_en_forma_canonica(db_session):
    copia.guardar_persona(
        db_session, PersonaSalutem.desde_api({"SALUTEM_ID": 501, "identificacion": "12.345.678-5"}), AHORA
    )
    copia.guardar_persona(
        db_session, PersonaSalutem.desde_api({"SALUTEM_ID": 502, "identificacion": "no-es-rut"}), AHORA
    )
    assert db_session.get(SalutemPersona, 501).rut == "123456785"
    assert db_session.get(SalutemPersona, 502).rut is None


def test_marca_desaparecidas_solo_las_no_vistas_y_la_reaparicion_limpia_la_marca(db_session):
    copia.guardar_cita(db_session, _cita(9001), AHORA)
    copia.guardar_cita(db_session, _cita(9002), AHORA)

    marcadas = copia.marcar_citas_desaparecidas(db_session, DIA, {9001}, DESPUES)

    assert marcadas == 1
    assert db_session.get(SalutemCita, 9001).desaparecida_en is None
    assert db_session.get(SalutemCita, 9002).desaparecida_en is not None
    assert copia.marcar_citas_desaparecidas(db_session, DIA, {9001}, DESPUES) == 0

    assert copia.guardar_cita(db_session, _cita(9002), DESPUES) is Resultado.CAMBIADO
    assert db_session.get(SalutemCita, 9002).desaparecida_en is None


def test_atencion_cambiada_queda_pendiente_de_vincular(db_session):
    copia.guardar_atencion(db_session, _atencion(), AHORA)
    fila = db_session.get(SalutemAtencion, 9001)
    fila.hash_vinculado = fila.hash_contenido

    assert copia.guardar_atencion(db_session, _atencion(anamnesis="editada"), DESPUES) is Resultado.CAMBIADO
    fila = db_session.get(SalutemAtencion, 9001)
    assert fila.hash_vinculado != fila.hash_contenido


def test_atencion_desaparecida_y_reaparecida_vuelve_a_quedar_pendiente(db_session):
    copia.guardar_atencion(db_session, _atencion(), AHORA)
    fila = db_session.get(SalutemAtencion, 9001)
    fila.hash_vinculado = fila.hash_contenido

    assert copia.marcar_atencion_desaparecida(db_session, 9001, DESPUES) is True
    assert copia.marcar_atencion_desaparecida(db_session, 9001, DESPUES) is False
    assert db_session.get(SalutemAtencion, 9001).hash_vinculado is None

    fila.hash_vinculado = fila.hash_contenido
    assert copia.guardar_atencion(db_session, _atencion(), DESPUES) is Resultado.CAMBIADO
    fila = db_session.get(SalutemAtencion, 9001)
    assert fila.desaparecida_en is None
    assert fila.hash_vinculado is None


def test_marcar_atencion_inexistente_no_hace_nada(db_session):
    assert copia.marcar_atencion_desaparecida(db_session, 123, AHORA) is False
