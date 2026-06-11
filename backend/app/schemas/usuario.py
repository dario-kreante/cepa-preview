from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Rol = Literal["Coordinacion", "Administrativo", "Auditor"]


class UsuarioCreate(BaseModel):
    username: str
    nombre: str
    password: str
    rol: Rol


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    password: str | None = None
    rol: Rol | None = None


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nombre: str
    rol: str
    activo: bool
    created_at: datetime
