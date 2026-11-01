"""Schemas Pydantic v2 para el módulo de Controles Médicos (EPIC-06).

Tres schemas de escritura independientes para alinear con las tres historias:
- ControlMedicoCreate  → CEPA-060 (registro base + cálculo de semana)
- ProximoControlUpdate → CEPA-061 (próximo control y estado de agenda)
- LicenciaUpdate       → CEPA-062 (licencia, GAF y RECA)
- EvaluacionUpdate     → evaluación clínica de la ficha del CEPA
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums_controles import EstadoReca, TipoLicencia, TipoReposo


class ControlMedicoCreate(BaseModel):
    """Alta de un control médico (CEPA-060).

    El campo semana_control NO se incluye: es calculado automáticamente
    en el servicio a partir de fecha_ingreso del Ingreso vinculado.
    """

    ingreso_id: int
    fecha_control: date
    # Se puede omitir si viene profesional_id: se usa el nombre del catálogo.
    medico_tratante: str | None = None
    region_derivacion: str
    # Profesional del catálogo (selector). Opcional: se puede escribir solo el nombre.
    profesional_id: int | None = None
    # Comentario libre del control (p. ej. "próximo a alta médica").
    observaciones: str | None = None

    @model_validator(mode="after")
    def _algun_medico(self) -> "ControlMedicoCreate":
        if not (self.medico_tratante and self.medico_tratante.strip()) and self.profesional_id is None:
            raise ValueError("Indique medico_tratante o profesional_id")
        return self


class ProximoControlUpdate(BaseModel):
    """Programación del próximo control (CEPA-061).

    Se aplica sobre un control ya existente vía PATCH.
    proximo_agendado por defecto False (RN-2).
    """

    proximo_control: date
    proximo_agendado: bool = False


class LicenciaUpdate(BaseModel):
    """Actualización de licencia y RECA asociados al control (CEPA-062).

    Si tiene_licencia=True: resumen_termino_lm, total_dias_lm, tipo_licencia y
    tipo_reposo son OBLIGATORIOS (RN-1).
    Si tiene_licencia=False: los campos de licencia quedan vacíos.
    GAF es siempre opcional pero, si se informa, debe estar en rango 0-100 (RN-3).
    estado_reca y observaciones siempre editables (RN-5).
    """

    tiene_licencia: bool
    resumen_termino_lm: str | None = None
    total_dias_lm: int | None = None
    tipo_licencia: TipoLicencia | None = None
    tipo_reposo: TipoReposo | None = None
    gaf: int | None = None
    # Tramo del catálogo gaf_tramo (v5 D18). Si no viene, se deriva del entero ``gaf``.
    gaf_tramo: str | None = Field(default=None, max_length=10)
    estado_reca: EstadoReca | None = None
    observaciones: str | None = None

    @field_validator("total_dias_lm")
    @classmethod
    def _dias_positivos(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("total_dias_lm debe ser un entero ≥ 1")
        return v

    @field_validator("gaf")
    @classmethod
    def _gaf_rango(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("GAF debe estar entre 0 y 100 (RN-3 CEPA-062)")
        return v

    @model_validator(mode="after")
    def _licencia_campos_obligatorios(self) -> "LicenciaUpdate":
        """Si tiene_licencia=True, exige los cuatro campos de licencia (RN-1)."""
        if self.tiene_licencia:
            faltantes = []
            if self.resumen_termino_lm is None:
                faltantes.append("resumen_termino_lm")
            if self.total_dias_lm is None:
                faltantes.append("total_dias_lm")
            if self.tipo_licencia is None:
                faltantes.append("tipo_licencia")
            if self.tipo_reposo is None:
                faltantes.append("tipo_reposo")
            if faltantes:
                raise ValueError(
                    f"Con tiene_licencia=True los siguientes campos son obligatorios: "
                    f"{', '.join(faltantes)}"
                )
        return self


def _vacio_a_none(v: str | None) -> str | None:
    if v is None:
        return None
    return v.strip() or None


class EvaluacionUpdate(BaseModel):
    """Evaluación clínica del control: los campos de la ficha del CEPA en SALUTEM.

    Todos opcionales y libres; un texto en blanco deja el campo vacío.
    """

    tiempo_estimado_tratamiento: str | None = Field(default=None, max_length=80)
    proyeccion_reintegro: str | None = Field(default=None, max_length=80)
    factores_riesgo: str | None = Field(default=None, max_length=500)

    _limpiar = field_validator(
        "tiempo_estimado_tratamiento", "proyeccion_reintegro", "factores_riesgo"
    )(_vacio_a_none)


class ControlMedicoRead(BaseModel):
    """Respuesta unificada del control médico (todos los campos de las tres historias)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    fecha_control: date
    semana_control: int
    medico_tratante: str
    region_derivacion: str
    # Profesional del catálogo; nulo si el médico se escribió a mano y no se pudo emparejar.
    profesional_id: int | None = None
    # CEPA-061
    proximo_control: date | None
    proximo_agendado: bool
    # CEPA-062
    tiene_licencia: bool
    resumen_termino_lm: str | None
    total_dias_lm: int | None
    tipo_licencia: TipoLicencia | None
    tipo_reposo: TipoReposo | None
    gaf: int | None
    # Tramo de GAF ("51-60"): el de SALUTEM o el elegido del catálogo gaf_tramo en SIGE.
    gaf_tramo: str | None = None
    estado_reca: EstadoReca | None
    observaciones: str | None
    # Evaluación clínica (ficha del CEPA)
    tiempo_estimado_tratamiento: str | None = None
    proyeccion_reintegro: str | None = None
    factores_riesgo: str | None = None
    # "CEPA" = cargado en SIGE; "SALUTEM" = creado por el sync desde una atención.
    origen: str = "CEPA"
    salutem_cita_id: int | None = None
    # Prestación/especialidad de SALUTEM de la atención que originó el control
    # ("Primera consulta médica AT"). Nula en los controles cargados en SIGE.
    especialidad: str | None = None
    # Campos corregidos a mano en SIGE: el sync de SALUTEM ya no los sobrescribe.
    campos_editados: list[str] = []
    # Cobertura de la ODA (D9): identificador de la ODA que cubre la fecha del control, y
    # fuera_de_oda=True si el ingreso tiene ODA pero ninguna cubre esa fecha.
    oda_que_cubre: str | None = None
    fuera_de_oda: bool = False

    @field_validator("campos_editados", mode="before")
    @classmethod
    def _separar_campos(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, str):
            return [c for c in v.split(",") if c]
        return v


class ArchivoControlRead(BaseModel):
    """Un documento de la biblioteca de SALUTEM unido al control por fecha."""

    model_config = ConfigDict(from_attributes=True)

    archivo_id: int
    nombre: str
    tipo: str | None
    fecha_creacion: datetime | None
