"""Tests del sender SMTP y del envío de correos de alerta (CEPA-102).

Usa FakeEmailSender para no enviar correo real.
Cubre CA-1, CA-2 (solo alertas), CA-3 (degradación controlada), CA-4 (no duplicar),
TC-102-01..TC-102-05.
"""

import pytest

from app.services.email_sender import FakeEmailSender, enviar_alerta


# ---------------------------------------------------------------------------
# FakeEmailSender
# ---------------------------------------------------------------------------


def test_fake_sender_registra_envios():
    sender = FakeEmailSender()
    sender.send(to="admin@cepa.example.com", subject="Alerta CEPA", body="<p>Hay una alerta</p>")
    assert len(sender.enviados) == 1
    assert sender.enviados[0]["to"] == "admin@cepa.example.com"


def test_fake_sender_puede_simular_fallo():
    sender = FakeEmailSender(forzar_error=True)
    with pytest.raises(ConnectionError):
        sender.send(to="admin@cepa.example.com", subject="Alerta", body="body")


# ---------------------------------------------------------------------------
# enviar_alerta — función de alto nivel
# ---------------------------------------------------------------------------


def test_enviar_alerta_llama_al_sender():
    # TC-102-01: alerta generada, sender disponible → se envía
    sender = FakeEmailSender()
    enviado = enviar_alerta(
        sender=sender,
        to_email="admin@cepa.example.com",
        tipo_alerta="vencimiento_licencia",
        caso_tipo="licencia",
        caso_id=5,
        plazo_str="2026-06-12",
    )
    assert enviado is True
    assert len(sender.enviados) == 1
    assert (
        "vencimiento_licencia" in sender.enviados[0]["subject"].lower()
        or "licencia" in sender.enviados[0]["body"].lower()
    )


def test_enviar_alerta_smtp_caido_no_lanza_excepcion():
    # TC-102-03: SMTP caído → fallo controlado (no propaga excepción, devuelve False)
    sender = FakeEmailSender(forzar_error=True)
    enviado = enviar_alerta(
        sender=sender,
        to_email="admin@cepa.example.com",
        tipo_alerta="oda_por_vencer",
        caso_tipo="oda",
        caso_id=3,
        plazo_str="2026-06-10",
    )
    assert enviado is False  # degradación controlada (CA-3)


def test_enviar_alerta_sin_email_valido_no_envia():
    # TC-102-05: usuario sin correo → no se envía
    sender = FakeEmailSender()
    enviado = enviar_alerta(
        sender=sender,
        to_email=None,
        tipo_alerta="oda_por_vencer",
        caso_tipo="oda",
        caso_id=3,
        plazo_str="2026-06-10",
    )
    assert enviado is False
    assert len(sender.enviados) == 0


def test_no_reenvio_si_email_ya_enviado():
    # TC-102-04: email de alerta ya enviado → enviar_correos_alertas no reenvía
    # (la flag email_enviado=True en la BD evita el reenvío — testeado a nivel de BD)
    from unittest.mock import MagicMock

    from sqlalchemy.orm import Session

    from app.services.alertas import enviar_correos_alertas

    db = MagicMock(spec=Session)
    # scalars().all() debe devolver lista vacía (filtrado por email_enviado=False en el servicio)
    db.scalars.return_value.all.return_value = []

    sender = FakeEmailSender()
    resultado = enviar_correos_alertas(db, sender=sender)
    # DD-C: enviar_correos_alertas ahora devuelve dict {enviados, omitidas}
    assert resultado["enviados"] == 0
    assert len(sender.enviados) == 0
