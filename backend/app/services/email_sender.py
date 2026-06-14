"""Sender SMTP inyectable para notificaciones de alerta (CEPA-102, D12).

Arquitectura:
- Protocolo `EmailSenderProtocol`: interfaz que implementan tanto SmtpEmailSender
  como FakeEmailSender (usado en tests).
- `enviar_alerta()`: función de alto nivel con degradación controlada (CA-3).

El correo se usa EXCLUSIVAMENTE para alertas (D12). No hay confirmaciones ni recordatorios.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocolo (interfaz)
# ---------------------------------------------------------------------------


@runtime_checkable
class EmailSenderProtocol(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None:
        """Envía un correo. Lanza ConnectionError si el SMTP no está disponible."""
        ...


# ---------------------------------------------------------------------------
# Implementación real: SmtpEmailSender
# ---------------------------------------------------------------------------


@dataclass
class SmtpConfig:
    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_addr: str = "cepa-alertas@utalca.cl"


class SmtpEmailSender:
    """Sender SMTP usando smtplib (stdlib). Inyectable en producción."""

    def __init__(self, config: SmtpConfig) -> None:
        self._config = config

    def send(self, *, to: str, subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._config.from_addr
        msg["To"] = to
        msg.attach(MIMEText(body, "html", "utf-8"))
        try:
            with smtplib.SMTP(self._config.host, self._config.port) as smtp:
                if self._config.use_tls:
                    smtp.starttls()
                if self._config.username:
                    smtp.login(self._config.username, self._config.password)
                smtp.sendmail(self._config.from_addr, [to], msg.as_string())
        except Exception as exc:
            raise ConnectionError(f"SMTP no disponible: {exc}") from exc


# ---------------------------------------------------------------------------
# Doble de tests: FakeEmailSender
# ---------------------------------------------------------------------------


@dataclass
class FakeEmailSender:
    """Sender falso para tests. Registra envíos en memoria; puede simular fallos."""

    forzar_error: bool = False
    enviados: list[dict] = field(default_factory=list)

    def send(self, *, to: str, subject: str, body: str) -> None:
        if self.forzar_error:
            raise ConnectionError("SMTP simulado no disponible")
        self.enviados.append({"to": to, "subject": subject, "body": body})


# ---------------------------------------------------------------------------
# Función de alto nivel: enviar_alerta (con degradación controlada)
# ---------------------------------------------------------------------------


def enviar_alerta(
    *,
    sender: EmailSenderProtocol,
    to_email: str | None,
    tipo_alerta: str,
    caso_tipo: str,
    caso_id: int,
    plazo_str: str,
) -> bool:
    """Envía el correo de una alerta. Devuelve True si se envió, False si no (sin excepción).

    Degradación controlada (CA-3): si el SMTP falla, registra el error y devuelve False.
    La alerta in-app sigue funcionando con independencia del resultado de esta función.
    Solo envía si to_email es un string no vacío (TC-102-05).
    """
    if not to_email:
        return False

    subject = f"[CEPA] Alerta: {tipo_alerta.replace('_', ' ').title()}"
    body = (
        f"<p>Estimado/a funcionario/a,</p>"
        f"<p>El sistema CEPA ha generado una alerta de tipo "
        f"<strong>{tipo_alerta.replace('_', ' ')}</strong> "
        f"para el {caso_tipo} ID {caso_id}.</p>"
        f"<p>Plazo: <strong>{plazo_str}</strong></p>"
        f"<p>Por favor ingrese al sistema para atender esta alerta.</p>"
        f"<p><em>Este correo es enviado exclusivamente para alertas de plazos perentorios."
        f"</em></p>"
    )
    try:
        sender.send(to=to_email, subject=subject, body=body)
        logger.info(
            "Correo de alerta enviado a %s (tipo=%s, caso_id=%d)",
            to_email,
            tipo_alerta,
            caso_id,
        )
        return True
    except ConnectionError as exc:
        logger.warning(
            "Fallo SMTP al enviar alerta (tipo=%s, caso_id=%d): %s",
            tipo_alerta,
            caso_id,
            exc,
        )
        return False
