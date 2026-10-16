"""Fase 2 (cita desde SALUTEM), Tarea 1: columnas de origen en ``cita``, configuración y alerta.

Cubre la migración 1360 (columnas nuevas, índice único de ``salutem_cita_id``, siembra de
``config_alerta`` para ``inasistencia``), las propiedades de configuración nuevas y el tipo de
alerta ``INASISTENCIA``.
"""

import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.enums_alertas import TipoAlerta
from app.models.cita import Cita
from app.models.config_alerta import ConfigAlerta
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


def _ingreso(db: Session, sufijo: str) -> Ingreso:
    pac = Paciente(rut=f"77{sufijo}", nombre="Paciente Cita SALUTEM", sexo="F", edad=40, region="Maule")
    db.add(pac)
    db.flush()
    ing = Ingreso(
        paciente_id=pac.id,
        folio=f"F-CSAL-{sufijo}",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 5),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32",
        estado="activo",
    )
    db.add(ing)
    db.flush()
    return ing


# ── Columnas de cita ────────────────────────────────────────────────────────


def test_cita_nueva_tiene_origen_sige_por_defecto(db_session: Session):
    ing = _ingreso(db_session, "001")
    cita = Cita(ingreso_id=ing.id, estado="agendada", fecha=datetime.date(2026, 10, 1))
    db_session.add(cita)
    db_session.flush()
    assert cita.origen == "SIGE"
    assert cita.salutem_cita_id is None
    assert cita.especialidad is None
    assert cita.profesional_nombre is None
    assert cita.profesional_id is None


def test_salutem_cita_id_unico(db_session: Session):
    ing = _ingreso(db_session, "002")
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add_all(
                [
                    Cita(
                        ingreso_id=ing.id,
                        estado="agendada",
                        fecha=datetime.date(2026, 10, 2),
                        salutem_cita_id=777,
                    ),
                    Cita(
                        ingreso_id=ing.id,
                        estado="agendada",
                        fecha=datetime.date(2026, 10, 3),
                        salutem_cita_id=777,
                    ),
                ]
            )


def test_salutem_cita_id_none_se_acepta_repetido(db_session: Session):
    ing = _ingreso(db_session, "003")
    db_session.add_all(
        [
            Cita(ingreso_id=ing.id, estado="agendada", fecha=datetime.date(2026, 10, 4)),
            Cita(ingreso_id=ing.id, estado="agendada", fecha=datetime.date(2026, 10, 5)),
        ]
    )
    db_session.flush()
    filas = db_session.scalars(select(Cita).where(Cita.ingreso_id == ing.id)).all()
    assert len(filas) == 2
    assert all(c.salutem_cita_id is None for c in filas)


# ── Migración: alerta inasistencia sembrada ─────────────────────────────────


def test_config_alerta_inasistencia_sembrada(db_session: Session):
    fila = db_session.scalars(
        select(ConfigAlerta).where(ConfigAlerta.tipo == "inasistencia")
    ).one()
    assert fila.activo is True
    assert fila.dias == 0
    assert fila.habiles is False
    assert fila.actualizado_por == "migracion"


def test_tipo_alerta_inasistencia():
    assert TipoAlerta.INASISTENCIA.value == "inasistencia"


# ── Configuración ───────────────────────────────────────────────────────────


def test_citas_salutem_desde_fecha_por_defecto_y_invalida():
    assert Settings(_env_file=None, citas_salutem_desde="2026-01-01").citas_salutem_desde_fecha == (
        datetime.date(2026, 1, 1)
    )
    assert Settings(_env_file=None).citas_salutem_desde == "2026-01-01"
    with pytest.raises(ValueError):
        _ = Settings(_env_file=None, citas_salutem_desde="x").citas_salutem_desde_fecha


def test_especialidades_reportes_set():
    cfg = Settings(_env_file=None, citas_especialidades_reportes=" Médico/a , Psicología ")
    assert cfg.citas_especialidades_reportes_set == frozenset({"médico/a", "psicología"})
    assert Settings(_env_file=None, citas_especialidades_reportes="").citas_especialidades_reportes_set == (
        frozenset()
    )
