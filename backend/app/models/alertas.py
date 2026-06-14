"""Modelos SQLAlchemy del módulo EPIC-10 — Alertas y Notificaciones.

Portabilidad D15: PK Identity/BigInteger, tipos genéricos, identificadores
≤30 chars en minúscula, fechas en UTC.

NOTA DE DISEÑO (Desviación 1): El modelo se llama AlertaNotif y usa la tabla
alerta_notif para evitar conflicto con app.models.farmacos.Alerta (tabla alerta,
EPIC-02). El plan original usaba el nombre Alerta/tabla alerta — ambas coexisten
en el sistema, siendo alerta la de recetas farmacológicas y alerta_notif la del
motor unificado de plazos perentorios de EPIC-10.
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlertaNotif(Base):
    """Alerta generada por el motor de plazos perentorios (CEPA-100).

    Columnas:
    - tipo:            TipoAlerta.value (String)
    - estado:          EstadoAlerta.value (String)
    - caso_id:         id del objeto de dominio disparador (ingreso, oda, ept, licencia)
    - caso_tipo:       nombre del tipo ('ingreso', 'oda', 'ept', 'licencia')
    - usuario_id:      id del usuario Administrativo destinatario
    - plazo_objetivo:  fecha del plazo perentorio evaluado (para idempotencia RN-4)
    - ventana_dias:    días de anticipación configurados para este tipo de alerta
    - generada_en:     timestamp UTC de creación
    - resuelta_en:     timestamp UTC de resolución (null si pendiente/leida)
    - email_enviado:   True si el correo de alerta fue enviado (CEPA-102)
    """

    __tablename__ = "alerta_notif"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    caso_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    caso_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    plazo_objetivo: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ventana_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    generada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    resuelta_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_enviado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
