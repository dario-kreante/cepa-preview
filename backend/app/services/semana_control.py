"""Cálculo puro de semana del control médico (CEPA-060 RN-3/RN-4).

Fórmula:
    semana_control = (fecha_control - fecha_ingreso).days // 7 + 1

La semana 1 cubre los días 0-6 desde la fecha de ingreso.
Si fecha_control == fecha_ingreso → semana 1.
Si fecha_control < fecha_ingreso → FechaControlInvalidaError.
"""

from datetime import date


class FechaControlInvalidaError(ValueError):
    """Se lanza cuando fecha_control es anterior a fecha_ingreso (CEPA-060 RN-4)."""


def calcular_semana_control(fecha_ingreso: date, fecha_control: date) -> int:
    """Devuelve el número de semana del control (entero ≥ 1).

    Args:
        fecha_ingreso: Fecha de ingreso del paciente al CEPA.
        fecha_control: Fecha del control médico.

    Returns:
        Número de semana transcurrida (≥ 1).

    Raises:
        FechaControlInvalidaError: Si fecha_control es anterior a fecha_ingreso.
    """
    delta = (fecha_control - fecha_ingreso).days
    if delta < 0:
        raise FechaControlInvalidaError(
            f"La fecha del control ({fecha_control}) es anterior a la fecha de ingreso "
            f"({fecha_ingreso}). El control no puede ser anterior al ingreso."
        )
    return delta // 7 + 1
