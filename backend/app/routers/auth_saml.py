"""SPIKE — Endpoints SAML del SP: metadata y ACS.

El IdP de UTalca autentica al usuario y hace POST de la aserción firmada al ACS.
Allí se valida la firma y solo entonces se resuelve el usuario del CEPA: el RUT
llega dentro de la aserción firmada, no en un parámetro manipulable.
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.jwt import crear_access_token, crear_refresh_token
from app.auth.saml.sp import (
    AsercionSamlInvalida,
    SsoSamlNoConfigurado,
    construir_url_login,
    generar_metadata_sp,
    validar_respuesta_saml,
)
from app.auth.saml.codigos import CodigoInvalido, almacen_codigos
from app.auth.sso.service import UsuarioSsoNoRegistrado, resolver_usuario_por_rut
from app.config import get_settings
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import CanjearCodigoRequest, TokenPair

router = APIRouter(prefix="/api/v1/auth/saml", tags=["auth"])


def _volver_al_login(motivo: str) -> RedirectResponse:
    """Devuelve el navegador al login del frontend indicando por qué falló.

    A /login y /acs llega el navegador por navegación, no el frontend por fetch:
    responder JSON dejaría a la persona en una pantalla técnica sin salida. El
    motivo es genérico a propósito —no distingue aserción inválida de usuario no
    habilitado— para no revelar de más a quien no logró autenticarse.
    """
    frontend = get_settings().frontend_url.rstrip("/")
    return RedirectResponse(
        f"{frontend}/login?sso_error={motivo}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/login")
def login(relay_state: str = "") -> RedirectResponse:
    """Inicia el flujo SAML: redirige al IdP de UTalca con un AuthnRequest.

    ``relay_state`` permite volver a la página desde la que se pidió el login;
    el IdP lo devuelve intacto al ACS.
    """
    settings = get_settings()
    try:
        url = construir_url_login(
            entity_id=settings.saml_sp_entity_id,
            acs_url=settings.saml_sp_acs_url,
            idp_cert=settings.saml_idp_cert,
            relay_state=relay_state,
        )
    except SsoSamlNoConfigurado:
        return _volver_al_login("no_configurado")
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/metadata")
def metadata() -> Response:
    """Metadata XML del SP, para entregar a DTI y registrar el SP en el IdP."""
    settings = get_settings()
    xml = generar_metadata_sp(
        entity_id=settings.saml_sp_entity_id,
        acs_url=settings.saml_sp_acs_url,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/acs")
def acs(
    SAMLResponse: str = Form(..., description="Aserción SAML emitida por el IdP"),
    RelayState: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Consume la aserción del IdP y devuelve el navegador al frontend.

    No entrega los tokens aquí: emite un código de un solo uso y redirige. Así la
    sesión no queda en la barra de direcciones ni en el historial, y el frontend
    la recoge por POST contra /canjear.
    """
    settings = get_settings()

    try:
        atributos = validar_respuesta_saml(
            saml_response_b64=SAMLResponse,
            entity_id=settings.saml_sp_entity_id,
            acs_url=settings.saml_sp_acs_url,
            idp_cert=settings.saml_idp_cert,
        )
        rut = _extraer_rut(atributos)
        usuario = resolver_usuario_por_rut(db, rut=rut, via="SAML")
    except (AsercionSamlInvalida, UsuarioSsoNoRegistrado):
        # Mismo destino en ambos casos: no se revela si el fallo fue de la
        # aserción o de la existencia del usuario.
        return _volver_al_login("autenticacion_fallida")

    db.commit()
    codigo = almacen_codigos.emitir(usuario_id=usuario.id)
    destino = f"{settings.frontend_url.rstrip('/')}/auth/callback?code={codigo}"
    if RelayState:
        destino += f"&redirect={quote(RelayState, safe='')}"
    return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/canjear", response_model=TokenPair)
def canjear(payload: CanjearCodigoRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Cambia un código de un solo uso por el par de tokens del CEPA."""
    try:
        usuario_id = almacen_codigos.canjear(payload.code)
    except CodigoInvalido:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido o expirado"
        )

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inexistente o desactivado"
        )

    return TokenPair(
        access_token=crear_access_token(usuario.id, usuario.username, usuario.rol),
        refresh_token=crear_refresh_token(usuario.id, usuario.username, usuario.rol),
    )


# Nombres bajo los que el IdP puede entregar el RUT. El de UTalca está por
# confirmar: se sabrá con la primera aserción real, y ampliar esta tupla es el
# único cambio que hará falta.
_ATRIBUTOS_RUT = ("rut", "RUT", "uid", "rol_uid", "urn:oid:1.3.6.1.4.1.25178.1.2.3")


def _extraer_rut(atributos: dict[str, list[str]]) -> str:
    for nombre in _ATRIBUTOS_RUT:
        valores = atributos.get(nombre)
        if valores:
            return valores[0]
    raise AsercionSamlInvalida(
        f"La aserción no trae ningún atributo de RUT reconocido (recibidos: {sorted(atributos)})"
    )
