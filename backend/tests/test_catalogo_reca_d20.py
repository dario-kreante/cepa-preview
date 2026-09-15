"""Decisiones v5 D20 — catálogo único de calificación RECA: EP · EC · AT · AC · NPE · No aplica.

El control médico (CEPA-062) y la RECA del reintegro (CEPA-041) usan el mismo
catálogo. El control guardaba antes un estado de flujo (pendiente/aprobado/...)
sin equivalente en la calificación: la migración lo deja en blanco y conserva
solo `no_aplica`.
"""

import datetime
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from app.domain.enums_controles import EstadoReca
from app.domain.reintegro_enums import TipoReca
from app.models.control_medico import ControlMedico

_MIGRACION = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "1240_calificacion_reca_d20.py"
)


def _cargar_migracion():
    spec = importlib.util.spec_from_file_location("migracion_1240", _MIGRACION)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_control_y_reintegro_comparten_el_catalogo():
    assert EstadoReca is TipoReca


def test_control_acepta_la_calificacion_d20(as_admin, ingreso_fixture):
    ctrl = as_admin.post(
        "/api/v1/controles-medicos",
        json={
            "ingreso_id": ingreso_fixture.id,
            "fecha_control": "2026-02-01",
            "semana_control": 3,
            "medico_tratante": "Dra. Rojas",
            "region_derivacion": "Maule",
        },
    )
    assert ctrl.status_code == 201, ctrl.text
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl.json()['id']}/licencia",
        json={"tiene_licencia": False, "estado_reca": "EC"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado_reca"] == "EC"


def test_control_rechaza_el_estado_de_flujo_anterior(as_admin, ingreso_fixture):
    ctrl = as_admin.post(
        "/api/v1/controles-medicos",
        json={
            "ingreso_id": ingreso_fixture.id,
            "fecha_control": "2026-02-01",
            "semana_control": 3,
            "medico_tratante": "Dra. Rojas",
            "region_derivacion": "Maule",
        },
    )
    r = as_admin.patch(
        f"/api/v1/controles-medicos/{ctrl.json()['id']}/licencia",
        json={"tiene_licencia": False, "estado_reca": "aprobado"},
    )
    assert r.status_code == 422


def test_migracion_limpia_estados_sin_equivalente(db_session, ingreso_fixture):
    anteriores = ["pendiente", "aprobado", "rechazado", "en_proceso", "no_aplica"]
    controles = [
        ControlMedico(
            ingreso_id=ingreso_fixture.id,
            fecha_control=datetime.date(2026, 2, 1),
            semana_control=i + 1,
            medico_tratante="Dra. Rojas",
            region_derivacion="Maule",
            estado_reca=estado,
        )
        for i, estado in enumerate(anteriores)
    ]
    db_session.add_all(controles)
    db_session.flush()

    with Operations.context(MigrationContext.configure(db_session.connection())):
        _cargar_migracion().upgrade()

    filas = db_session.execute(
        text("SELECT semana_control, estado_reca FROM control_medico WHERE ingreso_id = :id"),
        {"id": ingreso_fixture.id},
    ).all()
    assert dict(filas) == {1: None, 2: None, 3: None, 4: None, 5: "no_aplica"}
