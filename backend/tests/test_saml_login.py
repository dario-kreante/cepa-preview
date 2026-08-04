"""SPIKE — Inicio de sesión SAML: construcción del AuthnRequest.

Es el paso que falta para cerrar el circuito: el usuario entra a /login, el SP
arma un AuthnRequest y lo manda al IdP de UTalca por HTTP-Redirect; el IdP
autentica y devuelve la aserción al ACS.
"""

import base64
import zlib
from urllib.parse import parse_qs, urlparse

import pytest
from defusedxml import ElementTree as ET

SSO_UTALCA = "https://idprovider.utalca.cl/simplesaml/saml2/idp/SSOService.php"


def _decodificar_authn_request(saml_request: str) -> ET:
    """Deshace el binding HTTP-Redirect: base64 + DEFLATE crudo."""
    comprimido = base64.b64decode(saml_request)
    xml = zlib.decompress(comprimido, -15)
    return ET.fromstring(xml)


@pytest.fixture
def idp_configurado(monkeypatch):
    from app.config import get_settings
    from tests import saml_idp_falso as idp

    _, cert = idp.generar_par_de_claves()
    get_settings.cache_clear()
    monkeypatch.setenv("SAML_IDP_CERT", idp.cert_sin_cabeceras(cert))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_login_sin_sso_configurado_devuelve_al_frontend_con_el_motivo(client):
    """Sin certificado del IdP, /login no manda al usuario a autenticarse.

    A estos endpoints llega el navegador por navegación, no el frontend por
    fetch: responder un 503 con JSON deja a la persona en una pantalla técnica
    sin salida. Se la devuelve al login con el motivo, para poder explicárselo.
    """
    r = client.get("/api/v1/auth/saml/login", follow_redirects=False)

    assert r.status_code == 303
    destino = urlparse(r.headers["location"])
    assert destino.path == "/login"
    assert parse_qs(destino.query)["sso_error"] == ["no_configurado"]


def test_login_redirige_al_idp_de_utalca_con_un_authnrequest(client, idp_configurado):
    """GET /login devuelve una redirección al SSO del IdP con el AuthnRequest."""
    r = client.get("/api/v1/auth/saml/login", follow_redirects=False)

    assert r.status_code in (302, 303, 307), r.text
    destino = urlparse(r.headers["location"])
    assert f"{destino.scheme}://{destino.netloc}{destino.path}" == SSO_UTALCA

    query = parse_qs(destino.query)
    assert "SAMLRequest" in query, "la redirección debe llevar el AuthnRequest"


def test_authnrequest_declara_quien_pide_y_a_donde_responder(client, idp_configurado):
    """El AuthnRequest identifica al SP y fija el ACS donde espera la aserción.

    Si el Issuer no coincide con el entityID registrado, el IdP rechaza la
    petición; si el ACS no coincide, la aserción se enviaría a otro destino.
    """
    from app.config import get_settings

    r = client.get("/api/v1/auth/saml/login", follow_redirects=False)
    saml_request = parse_qs(urlparse(r.headers["location"]).query)["SAMLRequest"][0]

    raiz = _decodificar_authn_request(saml_request)
    settings = get_settings()

    assert raiz.get("Destination") == SSO_UTALCA
    assert raiz.get("AssertionConsumerServiceURL") == settings.saml_sp_acs_url
    assert raiz.get("ProtocolBinding") == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"

    issuer = raiz.find("{urn:oasis:names:tc:SAML:2.0:assertion}Issuer")
    assert issuer is not None and issuer.text == settings.saml_sp_entity_id


def test_authnrequest_imita_la_configuracion_que_utalca_ya_usa(client, idp_configurado):
    """El AuthnRequest se alinea con el que emite sprovider.utalca.cl.

    Decodificando el AuthnRequest real de UTalca (capturado siguiendo la cadena
    de redirects de huemul) se ve que NO envía RequestedAuthnContext y que pide
    NameIDPolicy Format=transient. Imitar la configuración ya probada contra ese
    IdP evita rechazos por un contexto de autenticación que quizá no soporte.

    Que el NameID sea transient implica además que el RUT llegará como atributo,
    no en el Subject.
    """
    r = client.get("/api/v1/auth/saml/login", follow_redirects=False)
    saml_request = parse_qs(urlparse(r.headers["location"]).query)["SAMLRequest"][0]
    raiz = _decodificar_authn_request(saml_request)

    ctx = raiz.find("{urn:oasis:names:tc:SAML:2.0:protocol}RequestedAuthnContext")
    assert ctx is None, "UTalca no envía RequestedAuthnContext; pedirlo arriesga un rechazo"

    politica = raiz.find("{urn:oasis:names:tc:SAML:2.0:protocol}NameIDPolicy")
    assert politica is not None
    assert politica.get("Format") == "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"


def test_relay_state_se_propaga_para_volver_al_origen(client, idp_configurado):
    """El RelayState viaja al IdP para poder devolver al usuario a donde estaba."""
    r = client.get(
        "/api/v1/auth/saml/login",
        params={"relay_state": "/dashboard"},
        follow_redirects=False,
    )

    query = parse_qs(urlparse(r.headers["location"]).query)
    assert query.get("RelayState") == ["/dashboard"]
