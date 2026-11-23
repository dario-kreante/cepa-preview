"""Modelo ``Convenio`` y largo de ``Ingreso.tipo_convenio`` (migración 1500)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.convenio import Convenio


def test_convenio_seleccionable_segun_visible_y_salutem(db_session):
    manual = Convenio(nombre="Convenio Rangers", nombre_normalizado="convenio rangers")
    inactivo = Convenio(
        nombre="Proyecto ISL Biobío",
        nombre_normalizado="proyecto isl biobio",
        salutem_id=1662,
        activo_salutem=False,
    )
    oculto = Convenio(
        nombre="Sin Convenio",
        nombre_normalizado="sin convenio",
        salutem_id=1415,
        visible=False,
    )
    db_session.add_all([manual, inactivo, oculto])
    db_session.flush()
    assert manual.seleccionable is True
    assert inactivo.seleccionable is False
    assert oculto.seleccionable is False


def test_nombre_normalizado_es_unico(db_session):
    db_session.add(Convenio(nombre="A", nombre_normalizado="a"))
    db_session.flush()
    db_session.add(Convenio(nombre="a", nombre_normalizado="a"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_tipo_convenio_acepta_120_caracteres(db_session, ingreso_fixture):
    ingreso_fixture.tipo_convenio = "x" * 120
    db_session.flush()
    db_session.refresh(ingreso_fixture)
    assert len(ingreso_fixture.tipo_convenio) == 120
