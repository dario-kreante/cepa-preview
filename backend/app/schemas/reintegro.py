"""Schemas Pydantic v2 del módulo de Seguimiento de Reintegro (EPIC-04).

Convenciones:
- *Create  → payload de entrada (validaciones de negocio en campo).
- *Update  → patch parcial (todos los campos opcionales).
- *Read    → respuesta (from_attributes=True).
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.enums import TipoDerivacion
from app.domain.reintegro_enums import EstadoReintegro, TipoAlta, TipoReca
from app.util.rut import RutInvalidoError, normalizar_rut


# ── CEPA-040: Caso de reintegro ────────────────────────────────────────────

class CasoReintegroCreate(BaseModel):
    """Alta de caso de reintegro. Campos obligatorios según D5/D6."""

    ingreso_id: int
    rut: str
    nombre: str
    tipo_derivacion: TipoDerivacion
    fecha_caso: date
    sexo: str          # "F" / "M" / "otro" — igual que Sexo de EPIC-01
    edad: int
    region: str
    # opcionales
    comuna: str | None = None
    rubro_empleador: str | None = None

    @field_validator("rut")
    @classmethod
    def _rut_valido(cls, v: str) -> str:
        try:
            return normalizar_rut(v)
        except RutInvalidoError as exc:
            raise ValueError(f"RUT inválido: {v!r}") from exc

    @field_validator("edad")
    @classmethod
    def _edad_positiva(cls, v: int) -> int:
        if v <= 0 or v > 130:
            raise ValueError("edad fuera de rango (1–130)")
        return v


class CasoReintegroUpdate(BaseModel):
    """Actualización parcial del caso (patch). Todos los campos son opcionales."""

    nombre: str | None = None
    tipo_derivacion: TipoDerivacion | None = None
    fecha_caso: date | None = None
    sexo: str | None = None
    edad: int | None = None
    region: str | None = None
    comuna: str | None = None
    rubro_empleador: str | None = None


class CasoReintegroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    rut: str
    nombre: str
    tipo_derivacion: TipoDerivacion
    fecha_caso: date
    sexo: str
    edad: int
    region: str
    comuna: str | None
    rubro_empleador: str | None
    estado_reintegro: EstadoReintegro
    fecha_reintegro: date | None
    remitido_isl: bool
    alta_medica: bool
    fecha_alta_medica: date | None
    alta_psicologica: bool
    fecha_alta_psico: date | None
    tipo_alta: TipoAlta | None
    observaciones: str | None


# ── CEPA-041: RECA y medidas correctivas ──────────────────────────────────

class RecaCreate(BaseModel):
    """Registro de RECA. Validaciones de coherencia temporal en el servicio."""

    fecha_reca: date
    tipo_reca: TipoReca
    numero_reca: str
    razon_social: str
    riesgos_calificados: str | None = None
    solicita_medidas: bool = False
    detalle_medidas: str | None = None
    fecha_medidas: date | None = None
    verifica_medidas: bool = False
    detalle_verificacion: str | None = None
    fecha_verificacion: date | None = None


class RecaUpdate(BaseModel):
    """Actualización parcial de la RECA."""

    fecha_reca: date | None = None
    tipo_reca: TipoReca | None = None
    numero_reca: str | None = None
    razon_social: str | None = None
    riesgos_calificados: str | None = None
    solicita_medidas: bool | None = None
    detalle_medidas: str | None = None
    fecha_medidas: date | None = None
    verifica_medidas: bool | None = None
    detalle_verificacion: str | None = None
    fecha_verificacion: date | None = None


class RecaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caso_reintegro_id: int
    fecha_reca: date
    tipo_reca: TipoReca
    numero_reca: str
    riesgos_calificados: str | None
    razon_social: str
    solicita_medidas: bool
    detalle_medidas: str | None
    fecha_medidas: date | None
    verifica_medidas: bool
    detalle_verificacion: str | None
    fecha_verificacion: date | None


# ── CEPA-042: Cierre / reintegro ──────────────────────────────────────────

class CierreReintegroUpdate(BaseModel):
    """Payload para actualizar el estado de reintegro y el cierre del caso.

    Las validaciones de coherencia temporal (fecha_reintegro >= fecha_reca,
    cierre requiere alta) se aplican en el servicio, no aquí.
    """

    estado_reintegro: EstadoReintegro
    fecha_reintegro: date | None = None
    remitido_isl: bool = False
    alta_medica: bool = False
    fecha_alta_medica: date | None = None
    alta_psicologica: bool = False
    fecha_alta_psico: date | None = None
    tipo_alta: TipoAlta | None = None
    observaciones: str | None = None
