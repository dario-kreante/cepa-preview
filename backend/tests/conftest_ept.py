"""Fixtures de apoyo para tests del módulo EPT (EPIC-03).

Se importan en los archivos de test de EPT vía:
  from tests.conftest_ept import ingreso_fixture  # noqa: F401
o bien declarando el fixture en conftest.py del proyecto.

Para usarlos con pytest, incluir en conftest.py raíz:
  from tests.conftest_ept import ingreso_fixture  # noqa: F401
"""

import datetime

import pytest

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


@pytest.fixture
def ingreso_fixture(db_session):
    """Crea un paciente + ingreso de prueba y devuelve el ingreso persistido."""
    paciente = Paciente(
        rut="123456785",
        nombre="Pedro Soto",
        sexo="M",
        edad=35,
        region="Maule",
    )
    db_session.add(paciente)
    db_session.flush()

    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio="F-2026-TEST",
        folio_manual=True,
        fecha_ingreso=datetime.date(2026, 1, 10),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Trastorno adaptativo",
        estado="activo",
    )
    db_session.add(ingreso)
    db_session.flush()
    return ingreso
