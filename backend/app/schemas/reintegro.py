"""Schemas Pydantic v2 del módulo de Seguimiento de Reintegro (EPIC-04).

Convenciones:
- *Create  → payload de entrada (validaciones de negocio en campo).
- *Update  → patch parcial (todos los campos opcionales).
- *Read    → respuesta (from_attributes=True).
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import TipoDerivacion
from app.domain.reintegro_enums import (
    EstadoReintegro,
    EstadoSolicitudReca,
    TipoAlta,
    TipoReca,
    TipoTrabajador,
)
from app.util.rut import RutInvalidoError, normalizar_rut


# ── CEPA-040: Caso de reintegro ────────────────────────────────────────────

class CasoReintegroCreate(BaseModel):
    """Alta de caso de reintegro. Campos obligatorios según D5/D6."""

    ingreso_id: int
    # Si no se indica, se toma el del paciente del ingreso (puede no tenerlo).
    rut: str | None = None
    nombre: str
    tipo_derivacion: TipoDerivacion
    fecha_caso: date
    region: str
    # opcionales
    # sexo/edad: el formulario ya no los pide (QA-008); sin valor se copian del paciente.
    sexo: str | None = None  # "F" / "M" / "otro" — igual que Sexo de EPIC-01
    edad: int | None = None
    comuna: str | None = None
    rubro_empleador: str | None = None
    # Sin valor se usa la razón social del ingreso (puede no tenerla).
    razon_social: str | None = None
    tipo_trabajador: TipoTrabajador | None = None
    # QA-010: ocupación del trabajador (el formulario la precarga, ver /precarga).
    ocupacion: str | None = Field(default=None, max_length=120)

    @field_validator("rut")
    @classmethod
    def _rut_valido(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        try:
            return normalizar_rut(v)
        except RutInvalidoError as exc:
            raise ValueError(f"RUT inválido: {v!r}") from exc

    @field_validator("edad")
    @classmethod
    def _edad_positiva(cls, v: int | None) -> int | None:
        if v is None:
            return None
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
    razon_social: str | None = None
    tipo_trabajador: TipoTrabajador | None = None
    ocupacion: str | None = Field(default=None, max_length=120)


class CasoReintegroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    rut: str | None
    nombre: str
    tipo_derivacion: TipoDerivacion
    fecha_caso: date
    sexo: str | None
    edad: int | None
    region: str
    comuna: str | None
    rubro_empleador: str | None
    razon_social: str | None
    tipo_trabajador: TipoTrabajador | None
    ocupacion: str | None = None
    estado_reintegro: EstadoReintegro
    fecha_reintegro: date | None
    remitido_isl: bool
    fecha_remitido_isl: date | None = None
    alta_medica: bool
    fecha_alta_medica: date | None
    alta_psicologica: bool
    fecha_alta_psico: date | None
    tipo_alta: TipoAlta | None
    observaciones: str | None
    fecha_solicitud_reca: date | None = None
    estado_solicitud_reca: EstadoSolicitudReca = EstadoSolicitudReca.PENDIENTE


class SolicitudRecaUpdate(BaseModel):
    """Registra o corrige la fecha en que se solicitó la RECA (QA-003)."""

    fecha_solicitud_reca: date


class RemisionIslUpdate(BaseModel):
    """Marca el caso «Remitido a ISL» (o corrige la fecha) sin cerrarlo (QA-010)."""

    fecha_remitido_isl: date


class PrecargaCasoRead(BaseModel):
    """Datos para precargar el alta de un caso (QA-010): de un caso anterior o de SALUTEM."""

    ocupacion: str | None = None
    tipo_trabajador: TipoTrabajador | None = None


class CasoPanelRead(BaseModel):
    """Fila de la lista global de casos activos de la pestaña Reintegro (QA-010)."""

    caso_id: int
    ingreso_id: int
    paciente_id: int
    paciente_nombre: str
    rut: str | None
    folio: str
    estado_reintegro: EstadoReintegro
    fecha_caso: date
    # Proyección más reciente registrada en los controles del ingreso.
    proyeccion: str | None = None
    fecha_proyeccion: date | None = None
    es_isl: bool
    estado_solicitud_reca: EstadoSolicitudReca
    # Pendientes (solo pacientes ISL): RECA sin solicitar y caso sin remitir a ISL.
    reca_por_solicitar: bool
    pendiente_remitir_isl: bool


class PendienteRegistroRead(BaseModel):
    """Paciente con alerta de proyección abierta y sin caso de reintegro activo (QA-010)."""

    paciente_id: int
    paciente_nombre: str
    rut: str | None
    ingreso_id: int
    folio: str
    alerta_id: int
    proyeccion: str | None
    fecha_control: date
    plazo_estimado: date | None = None


class PanelReintegroRead(BaseModel):
    activos: list[CasoPanelRead]
    pendientes_registro: list[PendienteRegistroRead]


class CasoActivoResumen(BaseModel):
    """Resumen de un caso activo para el aviso de caso repetido y el listado de duplicados."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    region: str
    razon_social: str | None
    fecha_caso: date
    estado_reintegro: EstadoReintegro


class PacienteConCasosRepetidosRead(BaseModel):
    """Paciente con más de un caso de reintegro activo (QA-003). Solo lectura."""

    paciente_id: int
    rut: str | None
    nombre: str
    casos: list[CasoActivoResumen]


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
