import pytest
from pydantic import ValidationError

from app.schemas.usuario import UsuarioCreate


def test_usuario_create_acepta_roles_validos():
    for rol in ("Coordinacion", "Administrativo", "Auditor"):
        u = UsuarioCreate(username="x", nombre="X", password="Clave123!", rol=rol)
        assert u.rol == rol


def test_usuario_create_rechaza_rol_clinico():
    with pytest.raises(ValidationError):
        UsuarioCreate(username="x", nombre="X", password="Clave123!", rol="Clinico")


def test_usuario_create_rechaza_rol_arbitrario():
    with pytest.raises(ValidationError):
        UsuarioCreate(username="x", nombre="X", password="Clave123!", rol="SuperUser")
