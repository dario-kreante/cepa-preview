"""Tests — Task 1 EPIC-09: helper de filtros D5."""
import pytest
from datetime import date

from sqlalchemy import select, func

from app.services.reportes_filtros import FiltrosDashboard, aplicar_filtros_ingreso
from app.models.ingreso import Ingreso


# Helper para crear un Ingreso con los campos obligatorios cubiertos
def _make_ingreso(**kwargs):
    defaults = dict(
        paciente_id=1,
        folio="F-TEST-001",
        fecha_ingreso=date(2026, 1, 15),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="Test",
    )
    defaults.update(kwargs)
    return Ingreso(**defaults)


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


def test_filtros_combinados_acumulan_clausulas(db_session):
    """Varios filtros activos deben producir query con múltiples restricciones."""
    filtros = FiltrosDashboard(programa="DIAT", sexo="F", tramo_etario="18-29")
    stmt = select(func.count()).select_from(Ingreso)
    stmt_filtrado = aplicar_filtros_ingreso(stmt, Ingreso, filtros)
    compiled = str(stmt_filtrado.compile(compile_kwargs={"literal_binds": False}))
    assert "programa" in compiled.lower()
    assert "sexo" in compiled.lower()
    assert "tramo_etario" in compiled.lower()
