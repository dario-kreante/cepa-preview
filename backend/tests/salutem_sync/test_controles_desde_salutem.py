"""Controles médicos creados automáticamente desde las atenciones de SALUTEM.

Cada atención con estado "Atendido" dentro de la ventana del ingreso se convierte en
un control del CEPA (origen SALUTEM), sin duplicarse al volver a vincular.
"""

from datetime import date

from sqlalchemy import select

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, EstadoCitaSalutem, PersonaSalutem
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.services.salutem_sync import copia
from app.services.salutem_sync.vinculacion import vincular
from tests.salutem_sync.conftest import AHORA

PERSONA = 1216017
ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)


def _paciente_e_ingreso(db, desde=date(2022, 6, 1)) -> Ingreso:
    paciente = Paciente(
        rut="390000022", nombre="Paciente Prueba", sexo="F", edad=35, region="Maule",
        salutem_persona_id=PERSONA,
    )
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(
        paciente_id=paciente.id, folio="F-2026-0064", folio_manual=True, fecha_ingreso=desde,
        tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
        diagnostico="prueba", estado="activo",
    )
    db.add(ingreso)
    db.flush()
    return ingreso


def _persona(db):
    copia.guardar_persona(
        db,
        PersonaSalutem.desde_api(
            {"SALUTEM_ID": PERSONA, "identificacion": "sin_id_1206850", "tipoIdentificacion": "SIN IDENTIFICACION"}
        ),
        AHORA,
    )


def _atencion(db, cita_id, fecha, *, estado=ATENDIDO, estado_nombre="Atendido", **contenido):
    crudo = {
        "personaId": PERSONA, "citaId": cita_id, "citaFecha": fecha, "estadoCitaId": estado,
        "estadoCitaNombre": estado_nombre, "especialidadNombre": "Médico/a",
        "profesionalNombre": "DRA. PAULA ROJAS", **contenido,
    }
    copia.guardar_atencion(db, AtencionSalutem.desde_api(crudo), AHORA)


def _cita(db, cita_id, fecha, estado):
    copia.guardar_cita(
        db,
        CitaSalutem.desde_api(
            {"personaId": PERSONA, "citaId": cita_id, "citaFecha": fecha,
             "citaFechaCreacion": f"{fecha} 08:00", "estadoCitaId": int(estado)}
        ),
        AHORA,
    )


def _controles(db) -> list[ControlMedico]:
    return list(db.scalars(select(ControlMedico).order_by(ControlMedico.fecha_control)))


def test_una_atencion_atendida_crea_un_control_con_los_datos_de_salutem(db_session):
    ingreso = _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(
        db_session, 5001, "2022-06-20",
        evolucionTratamiento=[{"nombre": "Evolución", "registro": "Paciente con ánimo bajo.<br>Se ajusta tratamiento."}],
    )

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert c.ingreso_id == ingreso.id
    assert (c.origen, c.salutem_cita_id) == ("SALUTEM", 5001)
    assert c.fecha_control == date(2022, 6, 20)
    assert c.semana_control == 3  # 19 días desde el ingreso → semana 3
    assert c.medico_tratante == "DRA. PAULA ROJAS"
    assert c.region_derivacion == "Maule"
    assert c.observaciones == "Paciente con ánimo bajo.\nSe ajusta tratamiento."
    assert c.tiene_licencia is False
    assert c.estado_reca is None


def test_la_indicacion_de_reposo_llena_la_licencia_y_el_gaf(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(
        db_session, 5002, "2024-04-14",
        indicaciones=[{"tipo": "Indicación", "nombre": "Indicación de Reposo",
                       "registro": "Se indica LM tipo 6 por 15 dias, fecha de inicio 14 de abril GAF 50"}],
    )

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert c.tiene_licencia is True
    assert (c.tipo_licencia, c.total_dias_lm, c.gaf) == ("6", 15, 50)
    assert "LM tipo 6" in c.resumen_termino_lm


def test_el_proximo_control_es_la_siguiente_cita_vigente_en_salutem(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5003, "2023-03-01")
    _cita(db_session, 5004, "2023-03-08", EstadoCitaSalutem.ANULADO)  # anulada: no cuenta
    _cita(db_session, 5005, "2023-03-15", EstadoCitaSalutem.AGENDADO)
    _cita(db_session, 5006, "2023-04-01", EstadoCitaSalutem.AGENDADO)

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert c.proximo_control == date(2023, 3, 15)
    assert c.proximo_agendado is True


def test_sin_cita_siguiente_no_hay_proximo_control(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5007, "2023-03-01")

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert (c.proximo_control, c.proximo_agendado) == (None, False)


def test_una_atencion_no_atendida_no_crea_control(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5008, "2023-03-01", estado=int(EstadoCitaSalutem.NO_ASISTE), estado_nombre="No Asiste")

    vincular(db_session, AHORA)

    assert _controles(db_session) == []


def test_volver_a_vincular_no_duplica_y_actualiza_sin_pisar_la_reca(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5009, "2023-03-01", profesionalNombre="DR. UNO")
    vincular(db_session, AHORA)
    [c] = _controles(db_session)
    c.estado_reca = "EC"  # lo completa una persona del CEPA
    db_session.flush()

    _atencion(db_session, 5009, "2023-03-01", profesionalNombre="DR. DOS")
    vincular(db_session, AHORA)
    vincular(db_session, AHORA, todo=True)

    [c] = _controles(db_session)
    assert c.medico_tratante == "DR. DOS"
    assert c.estado_reca == "EC"


def test_la_revision_completa_crea_controles_de_atenciones_ya_vinculadas(db_session):
    """Al desplegar, `vincular --todo` crea los controles de lo que ya estaba copiado."""
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5010, "2023-03-01")
    vincular(db_session, AHORA)
    db_session.execute(ControlMedico.__table__.delete())
    db_session.flush()

    vincular(db_session, AHORA, todo=True)

    assert [c.salutem_cita_id for c in _controles(db_session)] == [5010]


def test_los_controles_cargados_a_mano_siguen_siendo_del_cepa(db_session):
    ingreso = _paciente_e_ingreso(db_session)
    manual = ControlMedico(
        ingreso_id=ingreso.id, fecha_control=date(2023, 1, 10), semana_control=32,
        medico_tratante="Dr. Manual", region_derivacion="Maule",
    )
    db_session.add(manual)
    db_session.flush()

    assert (manual.origen, manual.salutem_cita_id) == ("CEPA", None)
