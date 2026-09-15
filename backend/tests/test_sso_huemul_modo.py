"""Acceso UTalca vía huemul controlado por flag (SSO_HUEMUL_MODO).

DTI conecta el SSO con validación de token recién en QA, pero el CEPA necesita
probar el flujo con la cuenta UTalca ya en DEV. Por eso existen tres modos:

- ``deshabilitado`` (por defecto): el callback no autentica a nadie.
- ``sin_verificar``: confía en el RUT que devuelve huemul. Es suplantable, así que
  **solo se respeta con ENTORNO=dev**; en cualquier otro entorno se trata como
  deshabilitado.
- ``token``: exige validar el token contra UTalca. Hasta que DTI entregue el
  mecanismo, el verificador rechaza (fail-closed).
"""

from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import get_settings
from app.models.usuario import Usuario

FRONTEND = "http://frontend.test"
CALLBACK = "http://backend.test/api/v1/auth/sso/callback"


@pytest.fixture
def configurar(monkeypatch):
    """Fija el entorno y el modo de huemul, y limpia la caché de settings."""

    def _configurar(*, entorno: str, modo: str) -> None:
        monkeypatch.setenv("ENTORNO", entorno)
        monkeypatch.setenv("SSO_HUEMUL_MODO", modo)
        monkeypatch.setenv("SSO_HUEMUL_CALLBACK_URL", CALLBACK)
        monkeypatch.setenv("FRONTEND_URL", FRONTEND)
        monkeypatch.setenv("SAML_IDP_CERT", "")
        get_settings.cache_clear()

    yield _configurar
    get_settings.cache_clear()


def _usuario(db: Session, *, rut: str, username: str) -> Usuario:
    u = Usuario(
        username=username,
        nombre="Usuario UTalca",
        hashed_password=hash_password("irrelevante-para-sso"),
        rol="Coordinacion",
        activo=True,
        rut=rut,
    )
    db.add(u)
    db.commit()
    return u


def _callback(client, rut: str):
    return client.get(
        "/api/v1/auth/sso/callback",
        params={"id": rut, "v": "1"},
        follow_redirects=False,
    )


# --------------------------------------------------------------------------- #
# Configuración por defecto
# --------------------------------------------------------------------------- #


def test_por_defecto_el_entorno_es_prod_y_huemul_esta_deshabilitado(monkeypatch):
    """Sin variables, nada queda abierto: olvidar configurar no habilita el atajo."""
    monkeypatch.delenv("ENTORNO", raising=False)
    monkeypatch.delenv("SSO_HUEMUL_MODO", raising=False)
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.entorno == "prod"
        assert s.sso_huemul_modo == "deshabilitado"
    finally:
        get_settings.cache_clear()


# --------------------------------------------------------------------------- #
# Inicio del login
# --------------------------------------------------------------------------- #


def test_login_deshabilitado_vuelve_al_login_con_aviso(client, configurar):
    configurar(entorno="dev", modo="deshabilitado")
    r = client.get("/api/v1/auth/sso/login", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"{FRONTEND}/login?sso_error=no_configurado"


def test_login_sin_verificar_en_dev_redirige_a_huemul_con_el_callback(client, configurar):
    configurar(entorno="dev", modo="sin_verificar")
    r = client.get("/api/v1/auth/sso/login", follow_redirects=False)
    assert r.status_code == 303
    destino = urlparse(r.headers["location"])
    assert f"{destino.scheme}://{destino.netloc}{destino.path}" == (
        "https://huemul.utalca.cl/sso/login.php"
    )
    assert parse_qs(destino.query)["url"] == [CALLBACK]


def test_login_sin_verificar_fuera_de_dev_no_redirige_a_huemul(client, configurar):
    """El atajo suplantable no puede activarse en QA ni en producción por error."""
    configurar(entorno="qa", modo="sin_verificar")
    r = client.get("/api/v1/auth/sso/login", follow_redirects=False)
    assert r.headers["location"] == f"{FRONTEND}/login?sso_error=no_configurado"


# --------------------------------------------------------------------------- #
# Callback
# --------------------------------------------------------------------------- #


def test_callback_sin_verificar_en_dev_entrega_un_codigo_canjeable(
    client, db_session: Session, configurar
):
    """Flujo completo en DEV: huemul devuelve el RUT sin DV y el usuario entra."""
    configurar(entorno="dev", modo="sin_verificar")
    _usuario(db_session, rut="16998654-1", username="dramirezr_test")

    r = _callback(client, "16998654")  # huemul entrega el RUT sin dígito verificador

    assert r.status_code == 303
    destino = urlparse(r.headers["location"])
    assert f"{destino.scheme}://{destino.netloc}{destino.path}" == f"{FRONTEND}/auth/callback"
    codigo = parse_qs(destino.query)["code"][0]
    # Los tokens nunca viajan en la URL.
    assert "access_token" not in r.headers["location"]

    canje = client.post("/api/v1/auth/saml/canjear", json={"code": codigo})
    assert canje.status_code == 200
    who = client.get(
        "/whoami-test", headers={"Authorization": f"Bearer {canje.json()['access_token']}"}
    )
    assert who.json()["username"] == "dramirezr_test"


def test_callback_sin_verificar_deja_traza_de_que_no_hubo_verificacion(
    client, db_session: Session, configurar
):
    """Cada ingreso por el atajo queda auditado como tal, para poder revisarlo."""
    from app.models.audit_log import AuditLog

    configurar(entorno="dev", modo="sin_verificar")
    _usuario(db_session, rut="16998654-1", username="dramirezr_audit")

    _callback(client, "16998654")

    acciones = db_session.scalars(
        select(AuditLog.action).where(AuditLog.actor == "dramirezr_audit")
    ).all()
    assert "LOGIN_SSO_SIN_VERIFICAR" in acciones


def test_callback_con_rut_sin_usuario_vuelve_al_login(client, db_session: Session, configurar):
    configurar(entorno="dev", modo="sin_verificar")
    r = _callback(client, "12345678")
    assert r.status_code == 303
    assert r.headers["location"] == f"{FRONTEND}/login?sso_error=autenticacion_fallida"


@pytest.mark.parametrize(
    ("entorno", "modo"),
    [
        ("dev", "deshabilitado"),
        ("qa", "sin_verificar"),
        ("prod", "sin_verificar"),
        # Modo token sin verificador real de DTI: sigue cerrado.
        ("dev", "token"),
        ("prod", "token"),
    ],
)
def test_callback_no_autentica_fuera_del_modo_permitido(
    client, db_session: Session, configurar, entorno, modo
):
    """Aunque el RUT exista y esté activo, solo DEV + sin_verificar deja entrar."""
    configurar(entorno=entorno, modo=modo)
    _usuario(db_session, rut="16998654-1", username=f"u_{entorno}_{modo}")

    r = _callback(client, "16998654")

    assert r.status_code == 303
    assert r.headers["location"] == f"{FRONTEND}/login?sso_error=autenticacion_fallida"
    assert "code=" not in r.headers["location"]
