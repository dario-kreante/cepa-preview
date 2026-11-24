from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Rol = Literal["Coordinacion", "Administrativo", "Auditor", "Superadmin"]


class UsuarioCreate(BaseModel):
    username: str
    nombre: str
    password: str
    rol: Rol
    # DD-C (CEPA-102): correo opcional para notificaciones de alerta
    email: str | None = None
    # CA-012: permiso extra «Acceso a Auditoría». Solo se guarda para Administrativo.
    acceso_auditoria: bool = False


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    password: str | None = None
    rol: Rol | None = None
    # DD-C (CEPA-102): correo opcional para notificaciones de alerta
    email: str | None = None
    # CA-012: permiso extra «Acceso a Auditoría». Solo se guarda para Administrativo.
    acceso_auditoria: bool | None = None


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nombre: str
    rol: str
    activo: bool
    email: str | None = None
    acceso_auditoria: bool = False
    created_at: datetime
