"""SPIKE — Endpoint ACS (Assertion Consumer Service) del SP SAML.

Es el punto donde el IdP de UTalca deposita la aserción tras autenticar. Aquí se
valida la firma y, solo entonces, se resuelve el usuario del CEPA y se emite el
JWT propio del sistema.

El RUT llega en la aserción firmada, no en un query param manipulable: esa es la
diferencia de fondo con el wrapper huemul.
"""

import pytest
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.usuario import Usuario
from tests import saml_idp_falso as idp


def _asegurar_rechazo(r) -> None:
    """El ACS devuelve al login con el motivo, y sin nada que sirva para entrar.

    El rechazo pasó de 401+JSON a redirección para que el usuario no quede en
    una pantalla técnica; lo que no cambia es que no se emite sesión, y eso es
    lo que estas comprobaciones vigilan.
    """
    from urllib.parse import parse_qs, urlparse

    assert r.status_code == 303, r.text
    destino = urlparse(r.headers["location"])
    assert destino.path == "/login"
    query = parse_qs(destino.query)
    assert query["sso_error"] == ["autenticacion_fallida"]
    # Ni tokens ni código canjeable: el rechazo no debe dejar puerta abierta.
    assert "code" not in query
    assert "access_token" not in r.headers["location"] and "eyJ" not in r.headers["location"]


ENTITY_ID = "https://sige-cepa.utalca.cl/saml/metadata"
ACS_URL = "https://sige-cepa.utalca.cl/api/v1/auth/saml/acs"


def _usuario(db: Session, *, rut: str, username: str, activo: bool = True) -> Usuario:
    u = Usuario(
        username=username,
        nombre="Usuario SAML",
        hashed_password=hash_password("no-se-usa-en-saml"),
        rol="Administrativo",
        activo=activo,
        rut=rut,
    )
    db.add(u)
    db.flush()
    return u


def test_acs_rechaza_si_no_hay_certificado_de_idp_configurado(client, db_session: Session):
    """Sin certificado del IdP configurado, el ACS no autentica a nadie.

    Mismo criterio fail-closed que el callback del wrapper: si no se puede
    verificar la firma, no se emite sesión — nunca se degrada a confiar en el
    contenido de la aserción.
    """
    _usuario(db_session, rut="16998654-1", username="pacs")
    db_session.commit()

    clave, cert = idp.generar_par_de_claves()
    resp = idp.construir_response(
        entity_id=ENTITY_ID, acs_url=ACS_URL, name_id="16998654",
        atributos={"rut": "16998654"},
    )
    idp.firmar_assertion(resp, clave_pem=clave, cert_pem=cert)

    r = client.post(
        "/api/v1/auth/saml/acs",
        data={"SAMLResponse": idp.response_b64(resp)},
        follow_redirects=False,
    )

    _asegurar_rechazo(r)


@pytest.fixture
def idp_configurado(monkeypatch):
    """Configura el SP con un IdP de pruebas y devuelve su par de claves."""
    from app.config import get_settings

    clave, cert = idp.generar_par_de_claves()
    get_settings.cache_clear()
    monkeypatch.setenv("SAML_SP_ENTITY_ID", ENTITY_ID)
    monkeypatch.setenv("SAML_SP_ACS_URL", ACS_URL)
    monkeypatch.setenv("SAML_IDP_CERT", idp.cert_sin_cabeceras(cert))
    get_settings.cache_clear()
    yield clave, cert
    get_settings.cache_clear()


def test_acs_con_asercion_firmada_autentica_al_usuario_correcto(
    client, db_session: Session, idp_configurado
):
    """Aserción válida → sesión para la identidad que venía firmada.

    El RUT viaja firmado dentro de la aserción, así que manipularlo invalida la
    firma. Eso es lo que hace confiable la identidad, a diferencia del `?id=RUT`
    del wrapper.

    El ACS ya no devuelve los tokens: redirige al frontend con un código de un
    solo uso (ver test_saml_codigo_canje.py). Aquí se sigue ese código hasta la
    sesión para comprobar a quién autentica.
    """
    from urllib.parse import parse_qs, urlparse

    clave, cert = idp_configurado
    _usuario(db_session, rut="16998654-1", username="psaml")
    db_session.commit()

    resp = idp.construir_response(
        entity_id=ENTITY_ID, acs_url=ACS_URL, name_id="16998654",
        atributos={"rut": "16998654"},  # el IdP entrega el RUT sin DV
    )
    idp.firmar_assertion(resp, clave_pem=clave, cert_pem=cert)

    r = client.post(
        "/api/v1/auth/saml/acs",
        data={"SAMLResponse": idp.response_b64(resp)},
        follow_redirects=False,
    )

    assert r.status_code == 303, r.text
    code = parse_qs(urlparse(r.headers["location"]).query)["code"][0]

    tokens = client.post("/api/v1/auth/saml/canjear", json={"code": code}).json()
    quien = client.get(
        "/whoami-test", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert quien.status_code == 200
    assert quien.json()["username"] == "psaml"


def test_acs_rechaza_asercion_firmada_por_otro_emisor(
    client, db_session: Session, idp_configurado
):
    """Una aserción con RUT válido pero firmada por otra clave no autentica.

    Es el ataque concreto: fabricar una aserción con el RUT de un funcionario y
    firmarla uno mismo. Contra el wrapper huemul funcionaría; aquí no.
    """
    _usuario(db_session, rut="16998654-1", username="pvictima")
    db_session.commit()

    clave_atacante, cert_atacante = idp.generar_par_de_claves(cn="IMPOSTOR")
    resp = idp.construir_response(
        entity_id=ENTITY_ID, acs_url=ACS_URL, name_id="16998654",
        atributos={"rut": "16998654"},
    )
    idp.firmar_assertion(resp, clave_pem=clave_atacante, cert_pem=cert_atacante)

    r = client.post(
        "/api/v1/auth/saml/acs",
        data={"SAMLResponse": idp.response_b64(resp)},
        follow_redirects=False,
    )

    _asegurar_rechazo(r)


def test_acs_rechaza_rut_sin_usuario_habilitado(client, db_session: Session, idp_configurado):
    """Aserción impecable, pero de alguien que no tiene acceso al CEPA."""
    clave, cert = idp_configurado

    resp = idp.construir_response(
        entity_id=ENTITY_ID, acs_url=ACS_URL, name_id="22222222",
        atributos={"rut": "22222222"},
    )
    idp.firmar_assertion(resp, clave_pem=clave, cert_pem=cert)

    r = client.post(
        "/api/v1/auth/saml/acs",
        data={"SAMLResponse": idp.response_b64(resp)},
        follow_redirects=False,
    )

    _asegurar_rechazo(r)


def test_metadata_sp_se_publica_como_xml(client):
    """El endpoint de metadata entrega el XML que se envía a DTI."""
    r = client.get("/api/v1/auth/saml/metadata")

    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]
    assert "AssertionConsumerService" in r.text
    assert "entityID" in r.text
