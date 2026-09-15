"""Verificación del ticket del SSO institucional de UTalca.

El SSO de UTalca (``huemul.utalca.cl/sso/login.php``) redirige de vuelta a la
aplicación con ``?id=<RUT>&v=<ticket>``. El RUT por sí solo NO es una credencial:
viaja en la URL y cualquiera puede escribirlo a mano. La única prueba de que el
usuario realmente se autenticó es el ticket ``v``, que debe verificarse contra
UTalca antes de emitir sesión.

Cómo se verifica ese ticket está pendiente de confirmación por DTI, así que la
verificación vive detrás de un Protocol —mismo patrón que la integración SALUTEM—
y el comportamiento por defecto es rechazar.
"""

from typing import Protocol, runtime_checkable


class TicketSsoInvalido(Exception):
    """El ticket no pudo verificarse contra UTalca, o no corresponde al RUT."""


@runtime_checkable
class SsoVerifierProtocol(Protocol):
    """Contrato de verificación del ticket SSO."""

    def verificar(self, *, rut: str, ticket: str) -> None:
        """Valida el ticket contra UTalca para el RUT indicado.

        Retorna None si el ticket es válido; lanza ``TicketSsoInvalido`` en
        cualquier otro caso. No devuelve booleano a propósito: obliga a manejar
        el fallo y evita que un valor falsy se interprete como éxito.
        """
        ...


class SsoVerifierNoConfigurado:
    """Verificador por defecto: rechaza todo (fail-closed).

    Se usa mientras DTI no confirme el mecanismo real de validación de ``v``.
    Rechazar por defecto implica que el SSO simplemente no autentica a nadie
    hasta que haya un verificador real; la alternativa (aceptar el RUT sin
    verificar) es justamente la vulnerabilidad que este diseño evita.
    """

    def verificar(self, *, rut: str, ticket: str) -> None:
        raise TicketSsoInvalido(
            "Verificación SSO no configurada: no se puede validar el ticket de UTalca"
        )


class SsoVerifierSinVerificacion:
    """Acepta el RUT que devuelve huemul sin verificar nada. **Suplantable.**

    Existe solo para probar el flujo con la cuenta UTalca en DEV mientras DTI
    habilita la validación del token (compromiso: QA). El router lo entrega
    únicamente con ``ENTORNO=dev`` y ``SSO_HUEMUL_MODO=sin_verificar``; cada
    ingreso queda auditado como ``LOGIN_SSO_SIN_VERIFICAR``.
    """

    def verificar(self, *, rut: str, ticket: str) -> None:  # noqa: ARG002
        if not rut.strip():
            raise TicketSsoInvalido("huemul no devolvió un RUT")
