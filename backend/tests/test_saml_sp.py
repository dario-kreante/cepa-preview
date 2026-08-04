"""SPIKE — Service Provider SAML 2.0 contra el IdP de la Universidad de Talca.

El wrapper ``huemul.utalca.cl/sso/login.php`` resultó no ser asegurable: devuelve
``v=1`` constante, sin nada que verificar (comprobado con un login real). Detrás
de ese wrapper hay un IdP SAML estándar —SimpleSAMLphp en
``idprovider.utalca.cl``— cuyo metadata y certificado son públicos, así que las
aserciones sí se pueden validar criptográficamente.

Estos tests cubren el lado que podemos construir sin depender de DTI: generar
nuestro metadata de SP (el insumo que ellos necesitan para registrarnos) y
validar aserciones firmadas.
"""

import pytest
from defusedxml import ElementTree as ET

# Certificado público del IdP de UTalca (CN=SRV-IDP, vigente hasta 2031), tomado de
# https://idprovider.utalca.cl/simplesaml/saml2/idp/metadata.php. Va incrustado para
# que los tests no dependan de la red ni del estado del servidor institucional.
_CERT_IDP_UTALCA = """MIIFHTCCA4WgAwIBAgIUHwei/axY81Kg8hS5CoeMFKy5U20wDQYJKoZIhvcNAQELBQAwgZ0xCzAJ
BgNVBAYTAkNMMQ4wDAYDVQQIDAVNQVVMRTEOMAwGA1UEBwwFVEFMQ0ExHTAbBgNVBAoMFFVOSVZF
UlNJREFEIERFIFRBTENBMRgwFgYDVQQLDA9JTkZSQUVTVFJVQ1RVUkExEDAOBgNVBAMMB1NSVi1J
RFAxIzAhBgkqhkiG9w0BCQEWFFBMQVRBRk9STUFAVVRBTENBLkNMMB4XDTIxMTAyODE1MTkxNloX
DTMxMTAyODE1MTkxNlowgZ0xCzAJBgNVBAYTAkNMMQ4wDAYDVQQIDAVNQVVMRTEOMAwGA1UEBwwF
VEFMQ0ExHTAbBgNVBAoMFFVOSVZFUlNJREFEIERFIFRBTENBMRgwFgYDVQQLDA9JTkZSQUVTVFJV
Q1RVUkExEDAOBgNVBAMMB1NSVi1JRFAxIzAhBgkqhkiG9w0BCQEWFFBMQVRBRk9STUFAVVRBTENB
LkNMMIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA69UNFmxw13ccOaPAnU49RNEuoHZX
7RHxW4y/InuczzG76DYBl7mTCZbUZJwil6RLzowbD0ulH+6zLEFJ4A22rmmVrbNb5I+PjOZq6EwT
A15Oc+ZDEEJP+bc5RC/7UnlQ5xBGcDHnjKtUKpGwnPILFNJpCTPnsxODJVMmHptR9BPfF+Va2tI7
z+nb9JYVprItIDLrZzni0u03xwekQNIkM2Q52qh55BoMy0/u2lPWOnqsdaqt6p3i8DuRbkLjBErN
I7UZEheJyhC5LLo1wvxa1QbyaVgbOtggSEhXDD7HUq640/YY3wnPu+ije4V1I0ryrD662eAOuM/v
i8wLgqcZ3PtSNZx/2Lwy7+Lxvb7jQMzooNfTUFlHiS7Lkn0qwBLMQluBQQ8LE1FSWs/4QWLTpm/o
lmruxwt+h+icpNYDzRKCdnHD1p5TSQpFsawbo4OAGsvIk8QDw75PQKjfAq4RGUQ/DwKNQdfGYDT/
nhexUhXvssXBLT6dz8zEUCvk5/jVAgMBAAGjUzBRMB0GA1UdDgQWBBStghgRuXDGX5lPFAm2dqqY
/TlTsDAfBgNVHSMEGDAWgBStghgRuXDGX5lPFAm2dqqY/TlTsDAPBgNVHRMBAf8EBTADAQH/MA0G
CSqGSIb3DQEBCwUAA4IBgQDfgYDd+/gURgYHyEStyh6Jq4aThpbwfrUs0wvkcNC1+lV0eaXznQ0F
lbUYR/aAgv1F+nL1QloFVfP/Dpj2WbaLq9HFxCa+5OZXD9o6D5i7poAOKjyW3R0BI9UXPHHL7R2l
EzlFEdwp+0TmKFW9ClKTfPvRxGNLF+a2wer+zlDNNEpqfmYLQSXikgl35BlZZPx8CG0wPtWqe4kt
tiy13JNA0JcOeNPDQwBUhLnfsnwKqHkzJhx1z1ZcPszSi7oHRq9YEHhfLgmPEx3XVkVi0PPEXIHl
1LjmhRWo2Si72WpaRcOobncBvHHBs7I7PxxTSB53uxjDJ8nlCy9cL8j0Hj1LKY34oWoCq/OrdppR
ctuDJV2hLbHcZqufDBPqF9Yx1uMzp3wFK/7cUbipJCqo+2qbHfB99Gi3DMGJmTX314ym6C3GBLZM
Cbbr1CoesQAZkvk8O6Sp6gyIjK3dFP8gyZ3kpsu2zkZiWcQsjqMtLbLtYT0Gl13Mmq2z/0E0c2kG
EUs="""

NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


def test_metadata_sp_declara_entityid_y_acs_configurados():
    """El metadata del SP declara quiénes somos y dónde recibimos la aserción.

    Es el documento que se entrega a DTI para el registro: sin entityID y
    AssertionConsumerService el IdP no sabría a quién responde ni a dónde.
    """
    from app.auth.saml.sp import generar_metadata_sp

    xml = generar_metadata_sp(
        entity_id="https://sige-cepa.utalca.cl/saml/metadata",
        acs_url="https://sige-cepa.utalca.cl/api/v1/auth/saml/acs",
    )

    raiz = ET.fromstring(xml)
    assert raiz.get("entityID") == "https://sige-cepa.utalca.cl/saml/metadata"

    acs = raiz.find(".//md:AssertionConsumerService", NS)
    assert acs is not None, "el metadata debe declarar un AssertionConsumerService"
    assert acs.get("Location") == "https://sige-cepa.utalca.cl/api/v1/auth/saml/acs"
    assert acs.get("Binding") == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"


def test_metadata_sp_exige_aserciones_firmadas():
    """El SP declara que solo acepta aserciones firmadas.

    Es la garantía que sustituye al `v=1` no verificable del wrapper: la
    identidad se acredita con una firma validable contra el certificado del IdP.
    """
    from app.auth.saml.sp import generar_metadata_sp

    xml = generar_metadata_sp(
        entity_id="https://sige-cepa.utalca.cl/saml/metadata",
        acs_url="https://sige-cepa.utalca.cl/api/v1/auth/saml/acs",
    )

    descriptor = ET.fromstring(xml).find(".//md:SPSSODescriptor", NS)
    assert descriptor is not None
    assert descriptor.get("WantAssertionsSigned") == "true"


ENTITY_ID = "https://sige-cepa.utalca.cl/saml/metadata"
ACS_URL = "https://sige-cepa.utalca.cl/api/v1/auth/saml/acs"


def test_asercion_firmada_por_el_idp_es_aceptada():
    """Una aserción bien firmada autentica y entrega sus atributos.

    Es la contraparte imprescindible de los tests de rechazo: sin este, un SP que
    rechazara absolutamente todo también los pasaría.
    """
    from app.auth.saml.sp import validar_respuesta_saml
    from tests import saml_idp_falso as idp

    clave, cert = idp.generar_par_de_claves()
    resp = idp.construir_response(
        entity_id=ENTITY_ID, acs_url=ACS_URL, name_id="16998654",
        atributos={"rut": "16998654"},
    )
    idp.firmar_assertion(resp, clave_pem=clave, cert_pem=cert)

    atributos = validar_respuesta_saml(
        saml_response_b64=idp.response_b64(resp),
        entity_id=ENTITY_ID,
        acs_url=ACS_URL,
        idp_cert=idp.cert_sin_cabeceras(cert),
    )

    assert atributos["rut"] == ["16998654"]


def test_asercion_sin_firma_es_rechazada():
    """Una aserción por lo demás válida, pero sin firma, no autentica a nadie.

    Todo lo demás está bien formado (Conditions, Audience, vigencia), así que el
    único motivo posible de rechazo es la firma ausente. Este es exactamente el
    agujero del wrapper huemul, donde `v=1` no acredita nada.
    """
    from app.auth.saml.sp import AsercionSamlInvalida, validar_respuesta_saml
    from tests import saml_idp_falso as idp

    _, cert = idp.generar_par_de_claves()
    resp = idp.construir_response(
        entity_id=ENTITY_ID, acs_url=ACS_URL, name_id="16998654",
        atributos={"rut": "16998654"},
    )

    with pytest.raises(AsercionSamlInvalida):
        validar_respuesta_saml(
            saml_response_b64=idp.response_b64(resp),
            entity_id=ENTITY_ID,
            acs_url=ACS_URL,
            idp_cert=idp.cert_sin_cabeceras(cert),
        )


def test_asercion_firmada_por_otra_clave_es_rechazada():
    """Una aserción firmada por un emisor distinto al IdP configurado se rechaza.

    Modela el ataque real: alguien fabrica una aserción con el RUT de otra
    persona y la firma con su propia clave. La firma es válida en sí misma, pero
    no proviene del IdP de UTalca.
    """
    from app.auth.saml.sp import AsercionSamlInvalida, validar_respuesta_saml
    from tests import saml_idp_falso as idp

    _, cert_legitimo = idp.generar_par_de_claves(cn="IDP-LEGITIMO")
    clave_atacante, cert_atacante = idp.generar_par_de_claves(cn="IDP-IMPOSTOR")

    resp = idp.construir_response(
        entity_id=ENTITY_ID, acs_url=ACS_URL, name_id="16998654",
        atributos={"rut": "16998654"},
    )
    idp.firmar_assertion(resp, clave_pem=clave_atacante, cert_pem=cert_atacante)

    with pytest.raises(AsercionSamlInvalida):
        validar_respuesta_saml(
            saml_response_b64=idp.response_b64(resp),
            entity_id=ENTITY_ID,
            acs_url=ACS_URL,
            idp_cert=idp.cert_sin_cabeceras(cert_legitimo),
        )
