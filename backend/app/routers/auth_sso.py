"""Acceso institucional UTalca: punto de entrada único y callback de huemul.

Flujo con huemul: el navegador va a ``/login``, que lo manda a
``huemul.utalca.cl/sso/login.php?url=<callback>``; UTalca autentica y devuelve el
navegador a ``/callback?id=<RUT>&v=<ticket>``.

A diferencia del sistema de reserva de salas, el callback apunta al backend y no
a una página del frontend: la identidad se decide server-side y la sesión se
entrega con un código de un solo uso canjeable por el JWT del CEPA, en vez de
una cookie con el RUT en texto plano.

Qué tanto se confía en el RUT lo decide ``SSO_HUEMUL_MODO`` (ver ``config.py``):
el modo ``sin_verificar`` solo se respeta con ``ENTORNO=dev``.
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.saml.codigos import almacen_codigos
from app.auth.sso.service import UsuarioSsoNoRegistrado, autenticar_sso
from app.auth.sso.verifier import (
    SsoVerifierNoConfigurado,
    SsoVerifierProtocol,
    SsoVerifierSinVerificacion,
    TicketSsoInvalido,
)
from app.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/auth/sso", tags=["auth"])


def _sin_verificar_habilitado(settings: Settings) -> bool:
    """El atajo suplantable solo vale en DEV; en QA y producción no se respeta."""
    return settings.sso_huemul_modo == "sin_verificar" and settings.entorno == "dev"


def _volver_al_login(motivo: str) -> RedirectResponse:
    frontend = get_settings().frontend_url.rstrip("/")
    return RedirectResponse(
        f"{frontend}/login?sso_error={motivo}", status_code=status.HTTP_303_SEE_OTHER
    )


def get_sso_verifier() -> SsoVerifierProtocol:
    """Verificador de identidad según el entorno y ``SSO_HUEMUL_MODO``.

    Es una dependencia de FastAPI para poder sustituirla por la implementación
    real de DTI (o por un doble en tests) sin tocar el endpoint. El modo
    ``token`` sigue siendo fail-closed hasta tener ese verificador.
    """
    if _sin_verificar_habilitado(get_settings()):
        return SsoVerifierSinVerificacion()
    return SsoVerifierNoConfigurado()


@router.get("/login")
def login() -> RedirectResponse:
    """Inicia el acceso con cuenta UTalca por el método habilitado en este entorno.

    Prioriza SAML (identidad firmada por el IdP) y cae a huemul solo si su modo
    está habilitado. Sin ninguno, devuelve al login con el aviso correspondiente.
    """
    settings = get_settings()
    if settings.saml_idp_cert:
        return RedirectResponse("/api/v1/auth/saml/login", status_code=status.HTTP_303_SEE_OTHER)
    if _sin_verificar_habilitado(settings):
        destino = (
            f"{settings.sso_huemul_login_url}"
            f"?url={quote(settings.sso_huemul_callback_url, safe='')}"
        )
        return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)
    return _volver_al_login("no_configurado")


@router.get("/callback")
def callback(
    id: str = Query(..., description="RUT que devuelve el SSO de UTalca"),
    v: str = Query("", description="Ticket que devuelve huemul (hoy la constante '1')"),
    db: Session = Depends(get_db),
    verifier: SsoVerifierProtocol = Depends(get_sso_verifier),
) -> RedirectResponse:
    """Resuelve la identidad que devuelve huemul y entrega la sesión al frontend."""
    via = "SSO_SIN_VERIFICAR" if isinstance(verifier, SsoVerifierSinVerificacion) else "SSO"
    try:
        usuario = autenticar_sso(db, rut=id, ticket=v, verifier=verifier, via=via)
    except (TicketSsoInvalido, UsuarioSsoNoRegistrado):
        # Mismo destino en ambos casos: no se revela si el RUT existe en el CEPA
        # a quien no ha acreditado ser esa persona.
        return _volver_al_login("autenticacion_fallida")

    db.commit()
    codigo = almacen_codigos.emitir(usuario_id=usuario.id)
    frontend = get_settings().frontend_url.rstrip("/")
    return RedirectResponse(
        f"{frontend}/auth/callback?code={codigo}", status_code=status.HTTP_303_SEE_OTHER
    )
