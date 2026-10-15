"""Copia de la biblioteca de SALUTEM para las personas con controles recientes."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.integrations.salutem.errors import SalutemAuthError
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion
from app.services.salutem_sync.archivos import refrescar_archivos
from tests.salutem_sync.conftest import AHORA

PERSONA = 1180505


def _control(db, cita_id=16625887, fecha=date(2026, 9, 15), persona=PERSONA) -> ControlMedico:
    paciente = Paciente(rut=f"39{cita_id}", nombre="P", sexo="M", edad=50, region="Maule")
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(paciente_id=paciente.id, folio=f"F-{cita_id}", folio_manual=True,
                      fecha_ingreso=date(2026, 8, 1), tipo_derivacion="DIEP", tipo_ingreso="convenio",
                      modelo_tratamiento="ambulatorio", diagnostico="prueba", estado="activo")
    db.add(ingreso)
    db.flush()
    db.add(SalutemAtencion(cita_id=cita_id, persona_id=persona, fecha_cita=fecha, contenido={},
                           hash_contenido="x", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
                           cambiado_en=AHORA))
    control = ControlMedico(ingreso_id=ingreso.id, origen="SALUTEM", salutem_cita_id=cita_id,
                            fecha_control=fecha, semana_control=7, medico_tratante="DRA",
                            region_derivacion="Maule")
    db.add(control)
    db.flush()
    return control


def _archivos(db) -> list[SalutemArchivo]:
    return list(db.scalars(select(SalutemArchivo).order_by(SalutemArchivo.archivo_id)))


def test_guarda_la_metadata_de_los_archivos_de_personas_con_control_reciente(db_session, salutem, ritmo):
    _control(db_session)
    salutem.agregar_archivo(1368688, PERSONA, nombre="boletaPPL ripley.pdf", creado="15-09-2026 16:29")

    r = refrescar_archivos(db_session, salutem, ritmo, AHORA)

    [a] = _archivos(db_session)
    assert (a.archivo_id, a.persona_id, a.nombre, a.tipo) == (1368688, PERSONA, "boletaPPL ripley.pdf", "documento")
    assert a.fecha_creacion == datetime(2026, 9, 15, 16, 29)
    assert a.desaparecido_en is None
    assert (r.personas, r.errores) == (1, [])
    assert not hasattr(a, "contenido")


def test_no_lista_personas_sin_control_reciente(db_session, salutem, ritmo):
    _control(db_session, fecha=date(2026, 8, 1))  # 46 días antes de AHORA
    salutem.agregar_archivo(1, PERSONA)

    refrescar_archivos(db_session, salutem, ritmo, AHORA)

    assert salutem.llamadas_a("listar_archivos") == []
    assert _archivos(db_session) == []


def test_un_archivo_que_ya_no_esta_queda_desaparecido_y_puede_volver(db_session, salutem, ritmo):
    _control(db_session)
    salutem.agregar_archivo(1, PERSONA)
    refrescar_archivos(db_session, salutem, ritmo, AHORA)
    del salutem.archivos[1]

    refrescar_archivos(db_session, salutem, ritmo, AHORA + timedelta(minutes=5))
    assert _archivos(db_session)[0].desaparecido_en is not None

    salutem.agregar_archivo(1, PERSONA)
    refrescar_archivos(db_session, salutem, ritmo, AHORA + timedelta(minutes=10))
    assert _archivos(db_session)[0].desaparecido_en is None


def test_salutem_caido_en_una_persona_no_detiene_a_las_demas(db_session, salutem, ritmo):
    _control(db_session, cita_id=1, persona=PERSONA)
    _control(db_session, cita_id=2, persona=PERSONA + 1)
    salutem.personas_archivos_caidas.add(PERSONA)
    salutem.agregar_archivo(9, PERSONA + 1)

    r = refrescar_archivos(db_session, salutem, ritmo, AHORA)

    assert [a.archivo_id for a in _archivos(db_session)] == [9]
    assert r.personas == 1
    assert len(r.errores) == 1 and str(PERSONA) in r.errores[0]


def test_una_credencial_rechazada_aborta(db_session, salutem, ritmo):
    _control(db_session)
    salutem.credencial_rechazada = True

    with pytest.raises(SalutemAuthError):
        refrescar_archivos(db_session, salutem, ritmo, AHORA)


def test_una_fecha_ilegible_se_guarda_nula(db_session, salutem, ritmo):
    _control(db_session)
    salutem.agregar_archivo(3, PERSONA, creado="ayer")

    refrescar_archivos(db_session, salutem, ritmo, AHORA)

    assert _archivos(db_session)[0].fecha_creacion is None
