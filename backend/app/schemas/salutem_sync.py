from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator


class EjecucionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modo: str
    estado: str
    inicio: datetime
    fin: datetime | None
    llamadas: int
    nuevos: int
    cambiados: int
    desaparecidos: int
    error: str | None

    @field_validator("inicio", "fin", mode="after")
    @classmethod
    def _asumir_utc_si_naive(cls, valor: datetime | None) -> datetime | None:
        # Oracle devuelve datetimes naive en UTC; sin esto, pydantic los serializa
        # sin offset y el consumidor no sabe en qué zona están.
        if valor is not None and valor.tzinfo is None:
            return valor.replace(tzinfo=timezone.utc)
        return valor


class EstadoSyncRead(BaseModel):
    ultimas: dict[str, EjecucionRead]
    primer_dia_con_datos: date | None
    personas: int
    citas: int
    atenciones: int
    # Atenciones de pacientes CEPA que aún no pasan a ficha_clinica.
    atenciones_pendientes: int
    # La última ejecución `caliente` exitosa terminó hace más de 20 minutos (o nunca).
    atrasado: bool
