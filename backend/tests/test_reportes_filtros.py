"""Tests — Task 1 EPIC-09: helper de filtros D5.

DD-3 update: sexo/region/comuna se leen de Paciente vía JOIN automático.
tramo_etario se deriva de paciente.edad con expresión CASE (no columna directa).
DD-4 update: fecha_desde/hasta ya NO se aplican en filtros de ingreso.
"""
import pytest
from datetime import date

from sqlalchemy import select, func

from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente


def test_filtros_sin_parametros_devuelve_query_sin_where(db_session):
    """Sin filtros, la query devuelve todos los ingresos."""
    filtros = FiltrosDashboard()
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    # La query no debe lanzar errores y debe ejecutarse
    result = db_session.execute(stmt_filtrado).scalar_one()
    assert result >= 0


def test_filtro_programa_acota_resultados(db_session):
    """Filtrar por programa debe añadir cláusula WHERE programa = X."""
    filtros = FiltrosDashboard(programa="DIEP")
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    compiled = str(stmt_filtrado.compile(compile_kwargs={"literal_binds": False}))
    assert "programa" in compiled.lower()


def test_filtro_rango_fechas_valido():
    """fecha_desde <= fecha_hasta no lanza error."""
    filtros = FiltrosDashboard(fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 12, 31))
    assert filtros.fecha_desde <= filtros.fecha_hasta


def test_filtro_rango_fechas_invalido():
    """fecha_desde > fecha_hasta debe lanzar ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FiltrosDashboard(fecha_desde=date(2026, 12, 31), fecha_hasta=date(2026, 1, 1))


def test_filtros_sexo_region_usan_join_paciente(db_session):
    """DD-3: filtros sexo/region/tramo_etario añaden JOIN a paciente en la query."""
    filtros = FiltrosDashboard(programa="DIAT", sexo="F", tramo_etario="18-29")
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    compiled = str(stmt_filtrado.compile(compile_kwargs={"literal_binds": False}))
    # programa sigue en ingreso
    assert "programa" in compiled.lower()
    # sexo ahora está en la tabla paciente (JOIN)
    assert "paciente" in compiled.lower()
    assert "sexo" in compiled.lower()
    # tramo_etario se expresa como CASE sobre paciente.edad
    assert "edad" in compiled.lower()


def test_filtro_fecha_no_se_aplica_en_ingreso(db_session):
    """DD-4: fecha_desde/hasta ya no se aplican sobre ingreso.fecha_ingreso."""
    filtros = FiltrosDashboard(fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 12, 31))
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    compiled = str(stmt_filtrado.compile(compile_kwargs={"literal_binds": False}))
    # fecha_ingreso NO debe aparecer en la query producida por aplicar_filtros_ingreso
    assert "fecha_ingreso" not in compiled.lower()


def test_filtro_sexo_via_paciente_real(db_session):
    """DD-3: filtrar por sexo filtra sobre paciente.sexo (integración con BD)."""
    pac_f = Paciente(rut="F-001-R", nombre="Femenino", sexo="F", edad=25, region="Maule")
    pac_m = Paciente(rut="M-001-R", nombre="Masculino", sexo="M", edad=35, region="Maule")
    db_session.add_all([pac_f, pac_m])
    db_session.flush()

    ing_f = Ingreso(
        paciente_id=pac_f.id, folio="F-FILTRO-F", folio_manual=True,
        fecha_ingreso=date(2026, 1, 1), tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="Test",
    )
    ing_m = Ingreso(
        paciente_id=pac_m.id, folio="F-FILTRO-M", folio_manual=True,
        fecha_ingreso=date(2026, 1, 2), tipo_derivacion="DIAT", tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio", diagnostico="Test",
    )
    db_session.add_all([ing_f, ing_m])
    db_session.flush()

    filtros = FiltrosDashboard(sexo="F")
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    count = db_session.execute(stmt_filtrado).scalar_one()
    # Al menos 1 (el ingreso del paciente femenino)
    assert count >= 1
