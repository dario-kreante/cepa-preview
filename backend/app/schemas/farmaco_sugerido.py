"""Fármacos sugeridos desde las recetas de SALUTEM (revisión humana)."""

from datetime import date

from pydantic import BaseModel

from app.domain.enums import FrecuenciaFarmaco


class FarmacoSugeridoRead(BaseModel):
    """Un medicamento leído de una receta de SALUTEM, estructurado para el esquema.

    `cita_fecha` es la atención más reciente que lo receta y sirve como fecha de
    emisión de la receta. `en_esquema` y `receta_registrada` dicen si ya se cargó.
    """

    ficha_clinica_id: int
    cita_fecha: date
    profesional: str | None
    texto: str
    medicamento: str
    dosis: str
    frecuencia: FrecuenciaFarmaco
    avisos: list[str]
    en_esquema: bool
    receta_registrada: bool
