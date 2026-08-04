"""SPIKE — Endpoints SAML del SP: metadata y ACS.

El IdP de UTalca autentica al usuario y hace POST de la aserción firmada al ACS.
Allí se valida la firma y solo entonces se resuelve el usuario del CEPA: el RUT
llega dentro de la aserción firmada, no en un parámetro manipulable.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.jwt import crear_access_token, crear_refresh_token
from app.auth.saml.sp import (
    AsercionSamlInvalida,
    generar_metadata_sp,
    validar_respuesta_saml,
)
from app.auth.sso.service import UsuarioSsoNoRegistrado, resolver_usuario_por_rut
from app.config import get_settings
from app.db.session import get_db
from app.schemas.auth import TokenPair

router = APIRouter(prefix="/api/v1/auth/saml", tags=["auth"])


@router.get("/metadata")
def metadata() -> Response:
    """Metadata XML del SP, para entregar a DTI y registrar el SP en el IdP."""
    settings = get_settings()
    xml = generar_metadata_sp(
        entity_id=settings.saml_sp_entity_id,
        acs_url=settings.saml_sp_acs_url,
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/acs", response_model=TokenPair)
def acs(
    SAMLResponse: str = Form(..., description="Aserción SAML emitida por el IdP"),
    db: Session = Depends(get_db),
) -> TokenPair:
    """Consume la aserción del IdP y emite el par de tokens del CEPA."""
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
        # Respuesta idéntica en ambos casos: no se revela si el fallo fue de la
        # aserción o de la existencia del usuario.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación SAML fallida"
        )

    db.commit()
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
