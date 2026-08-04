"""IdP SAML de pruebas: emite SAMLResponse firmadas con un par de claves propio.

Permite probar el SP sin depender de UTalca, y —más importante— distinguir un
rechazo por firma inválida de un rechazo por cualquier otro motivo. Sin esto, un
test que use una aserción incompleta pasa por la razón equivocada y da falsa
confianza sobre la verificación criptográfica.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import xmlsec
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree


def generar_par_de_claves(cn: str = "IDP-DE-PRUEBAS") -> tuple[str, str]:
    """Genera (clave_privada_pem, certificado_pem) autofirmado para tests."""
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    ahora = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - timedelta(days=1))
        .not_valid_after(ahora + timedelta(days=365))
        .sign(clave, hashes.SHA256())
    )
    pem_clave = clave.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pem_cert = cert.public_bytes(serialization.Encoding.PEM).decode()
    return pem_clave, pem_cert


def cert_sin_cabeceras(pem_cert: str) -> str:
    """Deja el certificado en el formato base64 plano que espera python3-saml."""
    return "".join(
        linea for linea in pem_cert.strip().splitlines() if "-----" not in linea
    )


def construir_response(
    *,
    entity_id: str,
    acs_url: str,
    name_id: str,
    idp_entity_id: str = "https://idprovider.utalca.cl/simplesaml/saml2/idp/metadata.php",
    atributos: dict[str, str] | None = None,
) -> etree._Element:
    """Arma una SAMLResponse completa y válida, aún sin firmar."""
    ahora = datetime.now(timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    emitida = ahora.strftime(fmt)
    expira = (ahora + timedelta(minutes=5)).strftime(fmt)

    attrs_xml = ""
    for nombre, valor in (atributos or {}).items():
        attrs_xml += (
            f'<saml:Attribute Name="{nombre}" '
            'NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">'
            f"<saml:AttributeValue>{valor}</saml:AttributeValue></saml:Attribute>"
        )
    attr_statement = f"<saml:AttributeStatement>{attrs_xml}</saml:AttributeStatement>" if attrs_xml else ""

    xml = f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_response1" Version="2.0" IssueInstant="{emitida}" Destination="{acs_url}">
  <saml:Issuer>{idp_entity_id}</saml:Issuer>
  <samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>
  <saml:Assertion ID="_assertion1" Version="2.0" IssueInstant="{emitida}">
    <saml:Issuer>{idp_entity_id}</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:unspecified">{name_id}</saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData NotOnOrAfter="{expira}" Recipient="{acs_url}"/>
      </saml:SubjectConfirmation>
    </saml:Subject>
    <saml:Conditions NotBefore="{emitida}" NotOnOrAfter="{expira}">
      <saml:AudienceRestriction><saml:Audience>{entity_id}</saml:Audience></saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AuthnStatement AuthnInstant="{emitida}" SessionIndex="_sesion1">
      <saml:AuthnContext>
        <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml:AuthnContextClassRef>
      </saml:AuthnContext>
    </saml:AuthnStatement>
    {attr_statement}
  </saml:Assertion>
</samlp:Response>"""
    return etree.fromstring(xml.encode())


def firmar_assertion(raiz: etree._Element, *, clave_pem: str, cert_pem: str) -> etree._Element:
    """Firma el elemento <Assertion> con RSA-SHA256, como hace un IdP real."""
    assertion = raiz.find("{urn:oasis:names:tc:SAML:2.0:assertion}Assertion")
    ref_id = assertion.get("ID")

    firma = xmlsec.template.create(
        assertion,
        xmlsec.Transform.EXCL_C14N,
        xmlsec.Transform.RSA_SHA256,
    )
    # La firma va tras <Issuer>, que es donde la espera el esquema SAML.
    assertion.insert(1, firma)

    ref = xmlsec.template.add_reference(
        firma, xmlsec.Transform.SHA256, uri=f"#{ref_id}"
    )
    xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
    xmlsec.template.add_transform(ref, xmlsec.Transform.EXCL_C14N)
    key_info = xmlsec.template.ensure_key_info(firma)
    xmlsec.template.add_x509_data(key_info)

    ctx = xmlsec.SignatureContext()
    ctx.key = xmlsec.Key.from_memory(clave_pem.encode(), xmlsec.KeyFormat.PEM)
    ctx.key.load_cert_from_memory(cert_pem.encode(), xmlsec.KeyFormat.CERT_PEM)
    # ID no es un atributo xml:id estándar; hay que registrarlo para que la
    # referencia "#_assertion1" resuelva al firmar.
    ctx.register_id(assertion, id_attr="ID")
    ctx.sign(firma)
    return raiz


def response_b64(raiz: etree._Element) -> str:
    return base64.b64encode(etree.tostring(raiz)).decode()
