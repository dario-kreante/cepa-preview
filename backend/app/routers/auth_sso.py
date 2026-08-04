"""SPIKE — Callback del SSO institucional de UTalca.

Flujo: el frontend manda al usuario a ``huemul.utalca.cl/sso/login.php?url=<este
endpoint>``; UTalca autentica y redirige aquí con ``?id=<RUT>&v=<ticket>``.

A diferencia del sistema de reserva de salas, el callback apunta al backend y no
a una página del frontend: el ticket se verifica server-side y la sesión se emite
con el JWT que ya usa el CEPA, en vez de una cookie con el RUT en texto plano.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.jwt import crear_access_token, crear_refresh_token
from app.auth.sso.service import UsuarioSsoNoRegistrado, autenticar_sso
from app.auth.sso.verifier import SsoVerifierNoConfigurado, TicketSsoInvalido
from app.db.session import get_db
from app.schemas.auth import TokenPair

router = APIRouter(prefix="/api/v1/auth/sso", tags=["auth"])


def get_sso_verifier() -> SsoVerifierNoConfigurado:
    """Verificador de ticket SSO en uso.

    Devuelve el verificador fail-closed mientras DTI no confirme cómo validar el
    parámetro ``v``. Es una dependencia de FastAPI para poder sustituirla por la
    implementación real (o por un doble en tests) sin tocar el endpoint.
    """
    return SsoVerifierNoConfigurado()


@router.get("/callback", response_model=TokenPair)
def callback(
    id: str = Query(..., description="RUT que devuelve el SSO de UTalca"),
    v: str = Query(..., description="Ticket de autenticación emitido por UTalca"),
    db: Session = Depends(get_db),
    verifier=Depends(get_sso_verifier),
) -> TokenPair:
    """Verifica el ticket de UTalca y emite el par de tokens del CEPA."""
    try:
        usuario = autenticar_sso(db, rut=id, ticket=v, verifier=verifier)
    except (TicketSsoInvalido, UsuarioSsoNoRegistrado):
        # Respuesta idéntica en ambos casos: no se revela si el RUT existe en el
        # CEPA a quien no ha acreditado ser esa persona.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación SSO fallida"
        )

    db.commit()
    return TokenPair(
        access_token=crear_access_token(usuario.id, usuario.username, usuario.rol),
        refresh_token=crear_refresh_token(usuario.id, usuario.username, usuario.rol),
    )
