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


def normalizar_rut(rut: str) -> str:
    """Lleva un RUT a la forma canónica que se almacena: ``16998654-1``.

    Quita puntos, espacios y separadores, y deja el dígito verificador en
    mayúscula tras un guión. El SSO de UTalca entrega el RUT con formato
    (reserva-salas lo limpia antes de usarlo), y los RUT cargados a mano suelen
    traer puntuación inconsistente; normalizar en un solo lugar evita que el
    login dependa de cómo venga escrito.
    """
    limpio = rut.strip().replace(".", "").replace("-", "").replace(" ", "").upper()
    if len(limpio) < 2:
        return limpio
    return f"{limpio[:-1]}-{limpio[-1]}"


def autenticar_sso(
    db: Session, *, rut: str, ticket: str, verifier: SsoVerifierProtocol
) -> Usuario:
    """Autentica a un usuario a partir del retorno del SSO de UTalca.

    Lanza ``TicketSsoInvalido`` si el ticket no se puede verificar, y
    ``UsuarioSsoNoRegistrado`` si nadie con ese RUT está habilitado en el CEPA.
    No hace commit: el caller decide la transacción.
    """
    verifier.verificar(rut=rut, ticket=ticket)

    usuario = db.scalars(
        select(Usuario).where(Usuario.rut == normalizar_rut(rut))
    ).one_or_none()
    # Mismo mensaje para "no existe" y "desactivado": no se revela cuál es el caso.
    if usuario is None or not usuario.activo:
        raise UsuarioSsoNoRegistrado("RUT sin usuario habilitado en el CEPA")

    # LOGIN_SSO, distinto de LOGIN: deja constancia de por qué vía entró.
    record_audit(
        db,
        actor=usuario.username,
        rol=usuario.rol,
        action="LOGIN_SSO",
        entity="usuario",
        entity_id=str(usuario.id),
    )
    db.flush()
    return usuario
