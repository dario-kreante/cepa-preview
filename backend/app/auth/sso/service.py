"""Autenticación vía SSO institucional de UTalca.

Orden deliberado: primero se verifica el ticket contra UTalca, y solo después se
busca el usuario. Así el endpoint no revela si un RUT existe en el CEPA a quien
no ha probado ser esa persona.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.sso.verifier import SsoVerifierProtocol
from app.models.usuario import Usuario


class UsuarioSsoNoRegistrado(Exception):
    """El RUT se autenticó en UTalca pero no tiene usuario habilitado en el CEPA."""


def _digito_verificador(cuerpo: str) -> str:
    """Calcula el DV de un RUT chileno por módulo 11."""
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def normalizar_rut(rut: str) -> str:
    """Lleva un RUT a la forma canónica que se almacena: ``16998654-1``.

    Quita puntos, espacios y separadores, y deja el dígito verificador en
    mayúscula tras un guión.

    El SSO de UTalca entrega el RUT **sin dígito verificador** (``16998654``),
    verificado contra huemul con un login real; las cargas manuales, en cambio,
    suelen traerlo con puntos y DV. Cuando falta el DV se calcula por módulo 11,
    de modo que ambas formas convergen al mismo valor y el login funciona venga
    como venga.
    """
    limpio = rut.strip().replace(".", "").replace(" ", "").upper()
    if not limpio:
        return limpio

    # El guión, o un DV 'K', delatan que el verificador ya viene incluido.
    if "-" in limpio:
        cuerpo, _, dv = limpio.rpartition("-")
        return f"{cuerpo}-{dv}" if cuerpo else limpio
    if limpio.endswith("K"):
        return f"{limpio[:-1]}-K"

    return f"{limpio}-{_digito_verificador(limpio)}"


def resolver_usuario_por_rut(db: Session, *, rut: str, via: str = "SSO") -> Usuario:
    """Resuelve el usuario del CEPA habilitado para un RUT ya acreditado.

    Presupone que la identidad **ya fue verificada** por el caller (firma SAML o
    ticket del wrapper); aquí solo se decide si esa persona tiene acceso.

    ``via`` queda en la traza de auditoría para distinguir por qué camino entró.
    Lanza ``UsuarioSsoNoRegistrado`` si el RUT no tiene usuario activo.
    """
    usuario = db.scalars(
        select(Usuario).where(Usuario.rut == normalizar_rut(rut))
    ).one_or_none()
    # Mismo mensaje para "no existe" y "desactivado": no se revela cuál es el caso.
    if usuario is None or not usuario.activo:
        raise UsuarioSsoNoRegistrado("RUT sin usuario habilitado en el CEPA")

    # Acción distinta de LOGIN: deja constancia de por qué vía entró.
    record_audit(
        db,
        actor=usuario.username,
        rol=usuario.rol,
        action=f"LOGIN_{via}",
        entity="usuario",
        entity_id=str(usuario.id),
    )
    db.flush()
    return usuario


def autenticar_sso(
    db: Session, *, rut: str, ticket: str, verifier: SsoVerifierProtocol
) -> Usuario:
    """Autentica a un usuario a partir del retorno del SSO de UTalca.

    Lanza ``TicketSsoInvalido`` si el ticket no se puede verificar, y
    ``UsuarioSsoNoRegistrado`` si nadie con ese RUT está habilitado en el CEPA.
    No hace commit: el caller decide la transacción.
    """
    verifier.verificar(rut=rut, ticket=ticket)
    return resolver_usuario_por_rut(db, rut=rut, via="SSO")
