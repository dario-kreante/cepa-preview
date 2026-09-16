from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
