"""Qué citas de la copia de SALUTEM cuentan como una hora vigente."""

from datetime import date

from sqlalchemy import ColumnElement, and_

from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.salutem_copia import SalutemCita

# Una cita anulada o a la que no asistió no es una hora vigente.
NO_VIGENTES = (int(EstadoCitaSalutem.ANULADO), int(EstadoCitaSalutem.NO_ASISTE))


def cita_vigente() -> ColumnElement[bool]:
    """Sin la comparación de fecha: la cita sigue en SALUTEM y no está anulada ni perdida."""
    return and_(
        SalutemCita.desaparecida_en.is_(None),
        SalutemCita.estado_id.not_in(NO_VIGENTES),
    )


def cita_vigente_desde(desde: date) -> ColumnElement[bool]:
    """Cita vigente cuya fecha es `desde` o posterior (hoy cuenta)."""
    return and_(SalutemCita.fecha_cita >= desde, cita_vigente())
