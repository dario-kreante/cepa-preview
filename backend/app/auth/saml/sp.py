"""Service Provider SAML 2.0 del SIGE-CEPA.

El IdP institucional es SimpleSAMLphp en ``idprovider.utalca.cl``; su metadata y
certificado son públicos, de modo que las aserciones se pueden validar
criptográficamente. Esa es la diferencia con el wrapper ``huemul``, que entrega
``v=1`` constante y no ofrece nada verificable.

``generar_metadata_sp`` produce el documento que se entrega a DTI para registrar
el SP en el IdP: sin él no pueden darnos de alta, así que es el primer paso y no
depende de ellos.
"""

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings


class AsercionSamlInvalida(Exception):
    """La respuesta SAML no superó la validación (firma, vigencia o destinatario)."""


def _settings_dict(*, entity_id: str, acs_url: str, cert_sp: str = "") -> dict:
    """Configuración del SP en el formato que espera python3-saml."""
    return {
        # strict=True: rechaza aserciones que no cumplan la especificación
        # (destinatario, vigencia, firma). Nunca debe apagarse.
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": entity_id,
            "assertionConsumerService": {
                "url": acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            # El IdP de UTalca publica NameIDFormat 'unspecified'.
            "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:unspecified",
            "x509cert": cert_sp,
            "privateKey": "",
        },
        # El IdP se completa desde su metadata público al validar aserciones.
        "idp": {
            "entityId": "https://idprovider.utalca.cl/simplesaml/saml2/idp/metadata.php",
            "singleSignOnService": {
                "url": "https://idprovider.utalca.cl/simplesaml/saml2/idp/SSOService.php",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": "",
        },
        "security": {
            # Exigir que la aserción venga firmada es lo que hace verificable la
            # identidad; sin esto el SP aceptaría cualquier POST.
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
        },
    }


def generar_metadata_sp(*, entity_id: str, acs_url: str, cert_sp: str = "") -> str:
    """Genera el metadata XML del SP para entregar a DTI."""
    settings = OneLogin_Saml2_Settings(
        _settings_dict(entity_id=entity_id, acs_url=acs_url, cert_sp=cert_sp),
        sp_validation_only=True,
    )
    metadata = settings.get_sp_metadata()

    errores = settings.validate_metadata(metadata)
    if errores:
        raise ValueError(f"Metadata SP inválido: {errores}")

    return metadata.decode("utf-8") if isinstance(metadata, bytes) else metadata


def validar_respuesta_saml(
    *, saml_response_b64: str, entity_id: str, acs_url: str, idp_cert: str
) -> dict[str, list[str]]:
    """Valida una SAMLResponse del IdP y devuelve los atributos de la aserción.

    Comprueba —vía python3-saml en modo estricto— que la aserción venga firmada
    por el IdP, esté vigente y sea para este SP. Lanza ``AsercionSamlInvalida``
    ante cualquier fallo: nunca devuelve datos de una aserción no verificada.
    """
    settings = _settings_dict(entity_id=entity_id, acs_url=acs_url)
    settings["idp"]["x509cert"] = idp_cert

    # python3-saml espera el entorno de la petición; se le arma el mínimo
    # necesario para el binding HTTP-POST.
    request_data = {
        "https": "on",
        "http_host": acs_url.split("//", 1)[-1].split("/", 1)[0],
        "script_name": "/" + acs_url.split("//", 1)[-1].split("/", 1)[-1],
        "post_data": {"SAMLResponse": saml_response_b64},
        "get_data": {},
    }

    auth = OneLogin_Saml2_Auth(request_data, old_settings=OneLogin_Saml2_Settings(settings))
    auth.process_response()

    errores = auth.get_errors()
    if errores or not auth.is_authenticated():
        motivo = auth.get_last_error_reason() or ", ".join(errores) or "aserción no autenticada"
        raise AsercionSamlInvalida(f"Respuesta SAML rechazada: {motivo}")

    return auth.get_attributes()
