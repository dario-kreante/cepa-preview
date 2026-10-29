"""Controles médicos creados automáticamente desde las atenciones de SALUTEM.

Cada atención con estado "Atendido" dentro de la ventana del ingreso se convierte en
un control del CEPA (origen SALUTEM), sin duplicarse al volver a vincular.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.config import get_settings

from app.integrations.salutem.models import AtencionSalutem, CitaSalutem, EstadoCitaSalutem, PersonaSalutem
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.services.control_medico import leer_controles, obtener_controles_por_ingreso
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


def test_el_gaf_por_tramo_y_el_tipo_de_reposo_vienen_de_los_campos_de_salutem(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(
        db_session, 5020, "2024-05-07",
        antecedentes=[
            {"agrupacion": "", "nombre": "Indicación de reposo", "registro": "Se extiende LM tipo 6 por 30 días"},
            {"agrupacion": "", "nombre": "GAF", "registro": {"1": "51-60"}},
            {"agrupacion": "", "nombre": "Tipo de reposo", "registro": "{'2': 'Parcial'}"},
        ],
    )

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert (c.gaf_tramo, c.gaf) == ("51-60", None)
    assert c.tiene_licencia is True
    assert (c.tipo_licencia, c.total_dias_lm, c.tipo_reposo) == ("6", 30, "parcial")


def test_indicacion_de_reposo_sin_la_palabra_licencia_es_licencia(db_session):
    """Caso real de QA (15-10-2026): "Reposo por 15 días" en Indicación de reposo."""
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(
        db_session, 5030, "2024-05-07",
        antecedentes=[
            {"nombre": "Indicación de reposo", "registro": "Reposo por 15 días desde el 07/05/2024"},
            {"nombre": "Tipo de reposo", "registro": {"1": "Total"}},
        ],
    )

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert c.tiene_licencia is True
    assert (c.total_dias_lm, c.tipo_reposo) == (15, "total")
    assert c.resumen_termino_lm == "Reposo por 15 días desde el 07/05/2024"


def test_sin_licencia_el_tipo_de_reposo_no_se_guarda(db_session):
    """El control solo guarda tipo de reposo cuando hay licencia (RN-1 de CEPA-062)."""
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(
        db_session, 5021, "2024-05-07",
        antecedentes=[
            {"nombre": "Indicación de reposo", "registro": "antecedente de prueba para ambiente de capacitación"},
            {"nombre": "GAF", "registro": {"1": "41-50"}},
            {"nombre": "Tipo de reposo", "registro": {"2": "Total"}},
        ],
    )

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert (c.tiene_licencia, c.tipo_reposo, c.gaf_tramo) == (False, None, "41-50")


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


def test_solo_las_atenciones_medicas_crean_control(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5011, "2023-03-01", especialidadNombre="Psicología")
    _atencion(db_session, 5012, "2023-03-02", especialidadNombre="Evaluación médica")
    _atencion(db_session, 5013, "2023-03-03")

    vincular(db_session, AHORA)

    # Desde QA-002 (22-10-2026) la Evaluación médica también es control.
    assert [c.salutem_cita_id for c in _controles(db_session)] == [5012, 5013]


def test_el_control_se_elimina_si_la_atencion_deja_de_ser_control(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5014, "2023-03-01")
    vincular(db_session, AHORA)
    assert len(_controles(db_session)) == 1

    _atencion(db_session, 5014, "2023-03-01", estado=int(EstadoCitaSalutem.ANULADO), estado_nombre="Anulado")
    vincular(db_session, AHORA)

    assert _controles(db_session) == []


def test_no_se_elimina_un_control_con_reca_registrada_por_el_cepa(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5015, "2023-03-01")
    vincular(db_session, AHORA)
    [c] = _controles(db_session)
    c.estado_reca = "EP"
    db_session.flush()

    _atencion(db_session, 5015, "2023-03-01", especialidadNombre="Psicología")
    vincular(db_session, AHORA)

    assert [c.salutem_cita_id for c in _controles(db_session)] == [5015]


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


def test_la_primera_consulta_medica_ep_tambien_es_control(db_session):
    """Especialidad con que el CEPA registra la primera consulta (ficha de prueba, 30-09-2026)."""
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5030, "2023-03-01", especialidadNombre="Primera consulta médica EP")

    vincular(db_session, AHORA)

    assert [c.salutem_cita_id for c in _controles(db_session)] == [5030]


def test_las_especialidades_de_control_se_configuran(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "salutem_especialidades_control", "Médico/a, Control psiquiátrico")
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5031, "2023-03-01", especialidadNombre="control PSIQUIÁTRICO")
    _atencion(db_session, 5032, "2023-03-02", especialidadNombre="Primera consulta médica EP")

    vincular(db_session, AHORA)

    assert [c.salutem_cita_id for c in _controles(db_session)] == [5031]


def test_la_ficha_de_prueba_del_cepa_llena_el_control(db_session):
    """Campos tal como los llenó el CEPA en la ficha de prueba del 30-09-2026."""
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(
        db_session, 5033, "2026-09-30", especialidadNombre="Primera consulta médica EP",
        indicaciones=[
            {"agrupacion": "Indicaciones", "nombre": "Indicaciones",
             "registro": "Fármacos:<br>Sertralina 50mg 0-1-0<br>Clotiazepam SOS"},
            {"agrupacion": "Indicaciones", "nombre": "Próximo control", "registro": "15 días"},
            {"agrupacion": "Indicaciones", "nombre": "Indicación de reposo",
             "registro": "Licencia tipo 6 por 15 días, fecha de inicio 30-09-2026"},
            {"agrupacion": "Indicaciones", "nombre": "GAF", "registro": ["51-60"]},
            {"agrupacion": "Indicaciones", "nombre": "Tipo de reposo", "registro": ["Total"]},
            {"agrupacion": "Indicaciones", "nombre": "Proyección de reintegro laboral", "registro": ["Más de 1 mes"]},
        ],
        antecedentes=[
            {"agrupacion": "Evaluación", "nombre": "Tiempo estimado de tratamiento", "registro": "3 meses"},
            {"agrupacion": "Evaluación", "nombre": "Factores de riesgo acogidos",
             "registro": "sobrecarga y hostilidad de jefatura"},
        ],
    )

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert (c.tiene_licencia, c.tipo_licencia, c.total_dias_lm, c.tipo_reposo) == (True, "6", 15, "total")
    assert c.gaf_tramo == "51-60"
    assert (c.proximo_control, c.proximo_agendado) == (date(2026, 10, 15), False)
    assert c.tiempo_estimado_tratamiento == "3 meses"
    assert c.proyeccion_reintegro == "Más de 1 mes"
    assert c.factores_riesgo == "sobrecarga y hostilidad de jefatura"


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("15 días", date(2023, 3, 16)), ("2 semanas", date(2023, 3, 15)), ("1 mes", date(2023, 4, 1)),
     ("en 3 meses", date(2023, 6, 1)), ("a evaluar", None)],
)
def test_sin_cita_agendada_el_proximo_control_sale_del_campo(db_session, texto, esperado):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5034, "2023-03-01",
              antecedentes=[{"nombre": "Próximo control", "registro": texto}])

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert (c.proximo_control, c.proximo_agendado) == (esperado, False)


def test_una_cita_agendada_manda_sobre_el_campo_proximo_control(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5035, "2023-03-01",
              antecedentes=[{"nombre": "Próximo control", "registro": "15 días"}])
    _cita(db_session, 5036, "2023-03-20", EstadoCitaSalutem.AGENDADO)

    vincular(db_session, AHORA)

    [c] = _controles(db_session)
    assert (c.proximo_control, c.proximo_agendado) == (date(2023, 3, 20), True)


ESPECIALIDADES_QA_002 = [
    "Médico/a", "Médico/a AT", "Primera consulta médica AT", "Primera consulta médica EP",
    "Psiquiatría", "Evaluación médica", "Evaluación médica AT", "Evaluación médica EP",
    "Evaluación médica PIPT", "Evaluación psiquiátrica", "Consultoría Psiquiátrica",
]


def test_todas_las_categorias_de_atencion_medica_son_control_por_defecto(db_session):
    """QA-002 (22-10-2026): la "Primera consulta médica AT" de Humberto no aparecía en
    Controles. Las categorías médicas/psiquiátricas de SALUTEM son control; las
    psicológicas, administrativas y de enfermería no."""
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    for i, especialidad in enumerate(ESPECIALIDADES_QA_002):
        _atencion(db_session, 5100 + i, f"2023-04-{i + 1:02d}", especialidadNombre=especialidad)
    for i, especialidad in enumerate(["Psicología", "Gestión administrativa", "Enfermería", "Uclínica"]):
        _atencion(db_session, 5200 + i, f"2023-05-{i + 1:02d}", especialidadNombre=especialidad)

    vincular(db_session, AHORA)

    assert [c.salutem_cita_id for c in _controles(db_session)] == [
        5100 + i for i in range(len(ESPECIALIDADES_QA_002))
    ]


def test_la_especialidad_se_compara_sin_tildes_ni_mayusculas(db_session):
    _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5300, "2023-06-01", especialidadNombre="PRIMERA CONSULTA MEDICA AT")
    _atencion(db_session, 5301, "2023-06-02", especialidadNombre="  Evaluacion  psiquiatrica ")
    _atencion(db_session, 5302, "2023-06-03", especialidadNombre="consultoría psiquiátrica")

    vincular(db_session, AHORA)

    assert [c.salutem_cita_id for c in _controles(db_session)] == [5300, 5301, 5302]


def test_la_lectura_del_control_trae_la_especialidad_de_salutem(db_session):
    """La UI de Controles distingue "Primera consulta médica AT" de "Médico/a"."""
    ingreso = _paciente_e_ingreso(db_session)
    _persona(db_session)
    _atencion(db_session, 5400, "2023-07-01", especialidadNombre="Médico/a")
    _atencion(db_session, 5401, "2023-07-02", especialidadNombre="Primera consulta médica AT")
    vincular(db_session, AHORA)
    manual = ControlMedico(
        ingreso_id=ingreso.id, fecha_control=date(2023, 7, 3), semana_control=1,
        medico_tratante="DR. MANUAL", region_derivacion="Maule",
    )
    db_session.add(manual)
    db_session.flush()

    leidos = leer_controles(db_session, obtener_controles_por_ingreso(db_session, ingreso.id))

    # Del más reciente al más antiguo.
    assert [(c.salutem_cita_id, c.especialidad) for c in leidos] == [
        (None, None), (5401, "Primera consulta médica AT"), (5400, "Médico/a"),
    ]
