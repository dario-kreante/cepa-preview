"""SPIKE — Entrega de la sesión al frontend mediante código de un solo uso.

El IdP hace POST de la aserción al ACS, así que el navegador termina en el
backend. Para pasarle la sesión al frontend sin exponer los tokens en la URL, el
ACS emite un código efímero y redirige; el frontend lo canjea por POST.

Los tokens nunca viajan en la barra de direcciones ni quedan en el historial.
"""

import pytest


def test_codigo_se_canjea_una_sola_vez():
    """Un código sirve exactamente una vez; el segundo canje falla.

    Si fuera reutilizable, quien viera la URL en el historial o en un log de
    proxy podría obtener una sesión válida más tarde.
    """
    from app.auth.saml.codigos import CodigoInvalido, AlmacenCodigos

    almacen = AlmacenCodigos()
    codigo = almacen.emitir(usuario_id=42)

    assert almacen.canjear(codigo) == 42
    with pytest.raises(CodigoInvalido):
        almacen.canjear(codigo)


def test_codigo_expirado_no_se_canjea():
    """Pasado el TTL el código deja de servir, aunque nadie lo haya usado."""
    from app.auth.saml.codigos import AlmacenCodigos, CodigoInvalido

    almacen = AlmacenCodigos(ttl_segundos=-1)  # ya nace vencido
    codigo = almacen.emitir(usuario_id=42)

    with pytest.raises(CodigoInvalido):
        almacen.canjear(codigo)


def test_codigo_inventado_no_se_canjea():
    """Un código que nunca se emitió no autentica a nadie."""
    from app.auth.saml.codigos import AlmacenCodigos, CodigoInvalido

    with pytest.raises(CodigoInvalido):
        AlmacenCodigos().canjear("codigo-inventado")


def test_acs_redirige_al_frontend_con_un_codigo(client, db_session, monkeypatch):
    """Tras validar la aserción, el ACS redirige al frontend con el código.

    Es lo que hace usable el flujo en un navegador: el usuario no ve JSON, y los
    tokens no viajan en la URL.
    """
    from app.auth.security import hash_password
    from app.config import get_settings
    from app.models.usuario import Usuario
    from tests import saml_idp_falso as idp

    entity_id = "https://sige-cepa.utalca.cl/saml/metadata"
    acs_url = "https://sige-cepa.utalca.cl/api/v1/auth/saml/acs"

    clave, cert = idp.generar_par_de_claves()
    get_settings.cache_clear()
    monkeypatch.setenv("SAML_IDP_CERT", idp.cert_sin_cabeceras(cert))
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")
    get_settings.cache_clear()

    db_session.add(
        Usuario(
            username="pcodigo", nombre="Con código",
            hashed_password=hash_password("x"), rol="Administrativo",
            activo=True, rut="16998654-1",
        )
    )
    db_session.commit()

    resp = idp.construir_response(
        entity_id=entity_id, acs_url=acs_url, name_id="16998654",
        atributos={"rut": "16998654"},
    )
    idp.firmar_assertion(resp, clave_pem=clave, cert_pem=cert)

    r = client.post(
        "/api/v1/auth/saml/acs",
        data={"SAMLResponse": idp.response_b64(resp)},
        follow_redirects=False,
    )

    assert r.status_code == 303, r.text
    destino = r.headers["location"]
    assert destino.startswith("http://localhost:5173")
    assert "code=" in destino
    # Los tokens no pueden viajar en la URL.
    assert "access_token" not in destino and "eyJ" not in destino

    # El frontend canjea el código por la sesión, y solo una vez.
    from urllib.parse import parse_qs, urlparse

    code = parse_qs(urlparse(destino).query)["code"][0]

    canje = client.post("/api/v1/auth/saml/canjear", json={"code": code})
    assert canje.status_code == 200, canje.text
    tokens = canje.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    quien = client.get(
        "/whoami-test", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert quien.status_code == 200
    assert quien.json()["username"] == "pcodigo"

    # Reutilizar el código no debe entregar otra sesión.
    assert client.post("/api/v1/auth/saml/canjear", json={"code": code}).status_code == 401

    get_settings.cache_clear()
