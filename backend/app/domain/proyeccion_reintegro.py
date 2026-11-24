"""Opciones del campo «Proyección de reintegro laboral» de SALUTEM (QA-010, 23-11-2026).

SALUTEM ofrece una lista cerrada. La clienta pidió alertar solo cuatro de ellas: «Paciente con
reintegro parcial» y «1, 2 y 3 semanas aproximadamente». Las demás («1 mes», «Más de 1 mes»,
«Paciente con reintegro total») y cualquier texto fuera de la lista no generan alerta.

Los valores se comparan sin tildes, mayúsculas ni espacios repetidos (``clave_especialidad``).
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.config import clave_especialidad


@dataclass(frozen=True)
class OpcionProyeccion:
    texto: str  # como lo muestra SALUTEM
    alerta: bool  # la clienta quiere aviso para esta opción
    dias: int | None  # plazo estimado desde la fecha del control; None = sin plazo (seguimiento)


OPCIONES: tuple[OpcionProyeccion, ...] = (
    OpcionProyeccion("1 semana aproximadamente", True, 7),
    OpcionProyeccion("2 semanas aproximadamente", True, 14),
    OpcionProyeccion("3 semanas aproximadamente", True, 21),
    OpcionProyeccion("1 mes aproximadamente", False, None),
    OpcionProyeccion("Más de 1 mes", False, None),
    OpcionProyeccion("Paciente con reintegro total", False, None),
    OpcionProyeccion("Paciente con reintegro parcial", True, None),
)


def _clave(valor: str) -> str:
    # Sin el punto final que a veces trae el texto libre.
    return clave_especialidad(valor).rstrip(" .")


_POR_CLAVE = {_clave(o.texto): o for o in OPCIONES}


def opcion_proyeccion(valor: str | None) -> OpcionProyeccion | None:
    """La opción de la lista de SALUTEM que corresponde al valor, o None si no es ninguna."""
    if not valor:
        return None
    return _POR_CLAVE.get(_clave(valor))


def opcion_alertable(valor: str | None) -> OpcionProyeccion | None:
    """La opción si es una de las cuatro que generan alerta; si no, None."""
    opcion = opcion_proyeccion(valor)
    return opcion if opcion is not None and opcion.alerta else None


def plazo_estimado(opcion: OpcionProyeccion, fecha_control: date) -> date | None:
    """Fecha estimada de reintegro: la del control más 7/14/21 días. Sin plazo, None."""
    return fecha_control + timedelta(days=opcion.dias) if opcion.dias is not None else None


def texto_alerta(opcion: OpcionProyeccion, fecha_control: date) -> str:
    """Detalle de la alerta: la opción y el plazo estimado (o «seguimiento» si no tiene plazo)."""
    plazo = plazo_estimado(opcion, fecha_control)
    if plazo is None:
        return f"{opcion.texto} · seguimiento del reintegro"
    return f"{opcion.texto} · reintegro estimado al {plazo.strftime('%d-%m-%Y')}"
