"""Licencias sugeridas desde las indicaciones de SALUTEM (revisión humana)."""

from datetime import date

from pydantic import BaseModel

from app.domain.enums_licencia import OrigenLicencia, TipoLicencia, TipoReposo


class LicenciaSugeridaRead(BaseModel):
    """Una licencia leída de una atención de SALUTEM, todavía sin registrar.

    Los campos que la indicación no trae quedan en None: los completa el
    administrativo al registrarla. `avisos` explica lo que conviene revisar.
    """

    ficha_clinica_id: int
    cita_fecha: date
    texto: str
    tipo_lm: TipoLicencia | None
    tipo_reposo: TipoReposo | None
    origen: OrigenLicencia
    fecha_inicio: date | None
    fecha_termino: date | None
    termino_calculado: bool
    cantidad_dias: int | None
    avisos: list[str]
    ya_registrada: bool
