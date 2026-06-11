"""Helper de filtros comunes para el dashboard y reportes de EPIC-09.

FiltrosDashboard centraliza los 14 filtros D5. aplicar_filtros_ingreso
aplica el subconjunto relevante a cualquier SELECT que incluya la tabla ingreso.

DD-3 (EPIC-09 rework): sexo, region, comuna se leen de Paciente via JOIN.
tramo_etario se deriva de paciente.edad en tiempo de consulta usando los tramos:
  18-29, 30-44, 45-59, 60+ (documentados aquí como referencia canónica).

DD-4 (EPIC-09 rework): fecha_desde/fecha_hasta se eliminaron de aplicar_filtros_ingreso;
el período se aplica exclusivamente sobre la tabla de hechos (Cita.fecha / LicenciaMedica.
fecha_emision) en cada router de reporte.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Select

# Tramos etarios canónicos (DD-3). Derivados de paciente.edad al momento de la consulta.
# 18-29 | 30-44 | 45-59 | 60+
# La función _tramo_case(Paciente) los expresa como expresión SQLAlchemy.

TRAMOS_ETARIOS = ["18-29", "30-44", "45-59", "60+"]


def _tramo_case(paciente_cls: Any) -> Any:
    """Expresión SQLAlchemy que mapea paciente.edad a su tramo etario canónico."""
    from sqlalchemy import case as sa_case

    return sa_case(
        (paciente_cls.edad < 18, "<18"),
        (paciente_cls.edad < 30, "18-29"),
        (paciente_cls.edad < 45, "30-44"),
        (paciente_cls.edad < 60, "45-59"),
        else_="60+",
    )


class FiltrosDashboard(BaseModel):
    """Parámetros de filtrado combinables (AND) para dashboard y reportes.

    Todos los campos son opcionales; None significa «sin restricción».
    fecha_desde/fecha_hasta se conservan para que los routers puedan
    pasarlos al constructor, pero NO los aplica aplicar_filtros_ingreso
    (DD-4: el período se aplica solo sobre la tabla de hechos).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Temporal — solo para compatibilidad con routers; NO se aplica en filtros de ingreso
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    granularidad: str | None = None  # "diario" | "semanal" | "mensual" | "anual"

    # Dimensiones de D5
    programa: str | None = None
    profesional_id: int | None = None
    especialidad: str | None = None
    tipo_atencion: str | None = None
    diagnostico: str | None = None
    tipo_alta: str | None = None
    tramo_etario: str | None = None   # filtro; derivado de paciente.edad
    sexo: str | None = None           # filtro; leído de paciente.sexo
    region: str | None = None         # filtro; leído de paciente.region
    comuna: str | None = None         # filtro; leído de paciente.comuna
    modelo_tratamiento: str | None = None
    tipo_ingreso: str | None = None
    tipo_convenio: str | None = None
    duracion: str | None = None  # relevante para telemedicina

    @model_validator(mode="after")
    def _validar_rango_fechas(self) -> "FiltrosDashboard":
        if self.fecha_desde and self.fecha_hasta:
            if self.fecha_desde > self.fecha_hasta:
                raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")
        return self


def aplicar_filtros_ingreso(
    stmt: Select,
    modelo_ingreso: Any,
    f: FiltrosDashboard,
    *,
    modelo_paciente: Any | None = None,
) -> Select:
    """Aplica los filtros activos de FiltrosDashboard a una SELECT sobre la tabla ingreso.

    Solo aplica los filtros cuyo valor no es None. Portable: usa ORM (sin SQL específico).

    DD-3: para filtros sexo/region/comuna/tramo_etario se necesita la tabla Paciente.
    Si modelo_paciente se provee se asume que el JOIN ya existe en stmt o se añade aquí.
    Si no se provee y hay filtros que lo requieren, se importa y se hace JOIN automático.

    DD-4: fecha_desde/fecha_hasta NO se aplican aquí (el período va solo sobre hechos).
    """
    # ── Filtros sobre ingreso directamente ────────────────────────────────────
    if f.programa is not None:
        stmt = stmt.where(modelo_ingreso.programa == f.programa)
    if f.profesional_id is not None:
        stmt = stmt.where(modelo_ingreso.profesional_id == f.profesional_id)
    if f.especialidad is not None:
        stmt = stmt.where(modelo_ingreso.especialidad == f.especialidad)
    if f.tipo_atencion is not None:
        stmt = stmt.where(modelo_ingreso.tipo_atencion == f.tipo_atencion)
    if f.diagnostico is not None:
        stmt = stmt.where(modelo_ingreso.diagnostico == f.diagnostico)
    if f.tipo_alta is not None:
        stmt = stmt.where(modelo_ingreso.tipo_alta == f.tipo_alta)
    if f.modelo_tratamiento is not None:
        stmt = stmt.where(modelo_ingreso.modelo_tratamiento == f.modelo_tratamiento)
    if f.tipo_ingreso is not None:
        stmt = stmt.where(modelo_ingreso.tipo_ingreso == f.tipo_ingreso)
    if f.tipo_convenio is not None:
        stmt = stmt.where(modelo_ingreso.tipo_convenio == f.tipo_convenio)

    # ── Filtros que requieren JOIN con Paciente ────────────────────────────────
    necesita_paciente = any(
        v is not None for v in (f.sexo, f.region, f.comuna, f.tramo_etario)
    )
    if necesita_paciente:
        pac = modelo_paciente
        if pac is None:
            from app.models.paciente import Paciente as _Paciente
            pac = _Paciente
            stmt = stmt.join(pac, modelo_ingreso.paciente_id == pac.id)

        if f.sexo is not None:
            stmt = stmt.where(pac.sexo == f.sexo)
        if f.region is not None:
            stmt = stmt.where(pac.region == f.region)
        if f.comuna is not None:
            stmt = stmt.where(pac.comuna == f.comuna)
        if f.tramo_etario is not None:
            stmt = stmt.where(_tramo_case(pac) == f.tramo_etario)

    return stmt
