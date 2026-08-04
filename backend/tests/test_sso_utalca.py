"""SPIKE — Autenticación SSO institucional UTalca (huemul.utalca.cl).

El SSO de UTalca redirige de vuelta con `?id=<RUT>&v=<ticket>`. El sistema de
reserva de salas confía en ese `id` sin verificar el `v`, lo que permite
suplantar a cualquier usuario abriendo el callback a mano. El CEPA maneja datos
clínicos, así que aquí el ticket se verifica server-side y la sesión se emite
con el JWT propio del sistema.

Cómo se verifica el ticket contra UTalca está pendiente de confirmación por DTI;
por eso la verificación vive detrás de un Protocol y el comportamiento por
defecto es rechazar (fail-closed).
"""

import pytest
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.usuario import Usuario


def _usuario_con_rut(db: Session, *, rut: str, username: str = "psso", activo: bool = True) -> Usuario:
    u = Usuario(
        username=username,
        nombre="Usuario SSO",
        hashed_password=hash_password("irrelevante-para-sso"),
        rol="Administrativo",
        activo=activo,
        rut=rut,
    )
    db.add(u)
    db.flush()
    return u


class _VerifierQueAcepta:
    """Verificador de prueba que acepta un único par (rut, ticket)."""

    def __init__(self, rut: str, ticket: str) -> None:
        self._esperado = (rut, ticket)

    def verificar(self, *, rut: str, ticket: str) -> None:
        from app.auth.sso.verifier import TicketSsoInvalido

        if (rut, ticket) != self._esperado:
            raise TicketSsoInvalido("Ticket no corresponde")


def test_verificador_no_configurado_rechaza_cualquier_ticket():
    """Sin verificador real configurado, ningún ticket se acepta (fail-closed).

    Es la garantía central del spike: mientras DTI no confirme cómo validar `v`,
    el SSO no puede autenticar a nadie. Nunca debe degradar a "confío en el RUT".
    """
    from app.auth.sso.verifier import SsoVerifierNoConfigurado, TicketSsoInvalido

    verifier = SsoVerifierNoConfigurado()

    with pytest.raises(TicketSsoInvalido):
        verifier.verificar(rut="11168636-K", ticket="ticket-cualquiera")


def test_ticket_invalido_no_autentica_aunque_el_rut_exista(db_session: Session):
    """Un RUT válido con ticket inválido no autentica.

    Reproduce el ataque que permite el sistema de reserva de salas: conocer el
    RUT de alguien no debe bastar para entrar como esa persona.
    """
    from app.auth.sso.service import autenticar_sso
    from app.auth.sso.verifier import TicketSsoInvalido

    _usuario_con_rut(db_session, rut="11168636-K")
    verifier = _VerifierQueAcepta(rut="11168636-K", ticket="ticket-bueno")

    with pytest.raises(TicketSsoInvalido):
        autenticar_sso(db_session, rut="11168636-K", ticket="ticket-falso", verifier=verifier)


def test_rut_valido_sin_usuario_en_cepa_no_autentica(db_session: Session):
    """Autenticarse en UTalca no da acceso al CEPA por sí solo.

    El SSO acredita identidad, no autorización: el acceso se otorga solo a quien
    Coordinación dio de alta. No se crea el usuario automáticamente.
    """
    from app.auth.sso.service import UsuarioSsoNoRegistrado, autenticar_sso

    verifier = _VerifierQueAcepta(rut="22222222-2", ticket="ticket-bueno")

    with pytest.raises(UsuarioSsoNoRegistrado):
        autenticar_sso(db_session, rut="22222222-2", ticket="ticket-bueno", verifier=verifier)


def test_usuario_desactivado_no_autentica_por_sso(db_session: Session):
    """Desactivar a alguien debe cerrarle también la puerta del SSO.

    Si el SSO ignorara `activo`, revocar un acceso dejaría de surtir efecto —
    la misma regla que ya aplica el login por contraseña (CEPA-001).
    """
    from app.auth.sso.service import UsuarioSsoNoRegistrado, autenticar_sso

    _usuario_con_rut(db_session, rut="33333333-3", username="pinactivo", activo=False)
    verifier = _VerifierQueAcepta(rut="33333333-3", ticket="ticket-bueno")

    with pytest.raises(UsuarioSsoNoRegistrado):
        autenticar_sso(db_session, rut="33333333-3", ticket="ticket-bueno", verifier=verifier)


def test_ticket_valido_autentica_y_deja_traza_de_auditoria(db_session: Session):
    """Ticket verificado + usuario habilitado → autentica, y queda auditado.

    La traza distingue LOGIN_SSO de LOGIN para poder responder por qué vía entró
    cada persona a datos clínicos.
    """
    from sqlalchemy import select

    from app.auth.sso.service import autenticar_sso
    from app.models.audit_log import AuditLog

    esperado = _usuario_con_rut(db_session, rut="44444444-4", username="pvalido")
    verifier = _VerifierQueAcepta(rut="44444444-4", ticket="ticket-bueno")

    usuario = autenticar_sso(
        db_session, rut="44444444-4", ticket="ticket-bueno", verifier=verifier
    )

    assert usuario.id == esperado.id
    acciones = db_session.scalars(
        select(AuditLog.action).where(AuditLog.entity_id == str(esperado.id))
    ).all()
    assert "LOGIN_SSO" in acciones


@pytest.mark.parametrize(
    "rut_del_sso",
    ["16.998.654-1", "16998654-1", "16998654-k".upper().replace("K", "1"), " 16998654-1 "],
)
def test_rut_se_normaliza_antes_de_buscar_al_usuario(db_session: Session, rut_del_sso: str):
    """El RUT se compara normalizado, venga como venga desde UTalca.

    reserva-salas limpia puntos y guiones del valor que entrega el SSO
    (hooks/useUser.ts), señal de que huemul lo devuelve con formato. Si aquí se
    comparara el string crudo, un mismo RUT con distinta puntuación no encontraría
    al usuario y el login fallaría de forma intermitente.
    """
    from app.auth.sso.service import autenticar_sso

    _usuario_con_rut(db_session, rut="16998654-1", username="pnorm")

    class _VerifierPermisivo:
        def verificar(self, *, rut: str, ticket: str) -> None:
            return None

    usuario = autenticar_sso(
        db_session, rut=rut_del_sso, ticket="t", verifier=_VerifierPermisivo()
    )

    assert usuario.username == "pnorm"


def test_callback_sso_rechaza_con_la_configuracion_por_defecto(client, db_session: Session):
    """El endpoint desplegado no autentica a nadie mientras no haya verificador.

    Este es el test que separa este diseño del de reserva-salas: allí, llamar al
    callback con el RUT de otra persona basta para entrar. Aquí devuelve 401
    aunque el RUT exista y esté activo, porque el ticket no se puede verificar.
    """
    _usuario_con_rut(db_session, rut="55555555-5", username="pcallback")
    db_session.commit()

    resp = client.get("/api/v1/auth/sso/callback", params={"id": "55555555-5", "v": "loquesea"})

    assert resp.status_code == 401
    assert "access_token" not in resp.text


def test_callback_con_verificador_real_emite_jwt_del_cepa(client, db_session: Session):
    """Con un verificador que valida el ticket, el callback emite el JWT del CEPA.

    Demuestra que enchufar la implementación real de DTI es lo único que falta:
    el resto del flujo ya funciona, y la sesión que entrega es el mismo par de
    tokens del login por contraseña — no una cookie de confianza.
    """
    from app.main import app
    from app.routers.auth_sso import get_sso_verifier

    _usuario_con_rut(db_session, rut="66666666-6", username="pjwt")
    db_session.commit()

    app.dependency_overrides[get_sso_verifier] = lambda: _VerifierQueAcepta(
        rut="66666666-6", ticket="ticket-bueno"
    )
    try:
        resp = client.get(
            "/api/v1/auth/sso/callback", params={"id": "66666666-6", "v": "ticket-bueno"}
        )
    finally:
        app.dependency_overrides.pop(get_sso_verifier, None)

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["access_token"]
    assert cuerpo["refresh_token"]

    # El token emitido sirve de verdad, y la identidad que lleva es la correcta.
    protegida = client.get(
        "/whoami-test", headers={"Authorization": f"Bearer {cuerpo['access_token']}"}
    )
    assert protegida.status_code == 200
    assert protegida.json()["username"] == "pjwt"
