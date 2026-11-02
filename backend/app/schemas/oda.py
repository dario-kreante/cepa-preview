from datetime import date

from pydantic import BaseModel, ConfigDict


class OdaCreate(BaseModel):
    """Registro de ODA. La fecha de vencimiento es obligatoria (CEPA-015 RN-2)."""

    identificador: str
    fecha_vencimiento: date


class OdaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    identificador: str
    fecha_vencimiento: date
    vigente: bool


class OdaAlerta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingreso_id: int
    identificador: str
    fecha_vencimiento: date


# ── Importación del Reporte Prestador del ISL (QA-004) ─────────────────────────


class OdaImportFilaSinPaciente(BaseModel):
    """Fila del reporte que no calzó con ningún ingreso (ni por siniestro ni por RUT)."""

    fila: int
    numero_orden: str
    tipo_orden: str | None = None
    numero_siniestro: str | None = None
    rut_trabajador: str | None = None


class OdaImportError(BaseModel):
    fila: int
    motivo: str


class OdaImportPorVencer(BaseModel):
    oda_id: int
    ingreso_id: int
    folio: str
    numero_orden: str
    fecha_vencimiento: date


class OdaImportResumen(BaseModel):
    """Resumen de la carga. Con dry_run=true nada se guarda: es la previsualización."""

    dry_run: bool
    archivo: str | None = None
    filas_leidas: int
    creadas: int
    actualizadas: int
    sin_cambios: int
    match_por_siniestro: int
    match_por_rut: int
    sin_paciente: list[OdaImportFilaSinPaciente]
    errores: list[OdaImportError]
    ventana_dias: int
    por_vencer_paciente_activo: int
    por_vencer: list[OdaImportPorVencer]
