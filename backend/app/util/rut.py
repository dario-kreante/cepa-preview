"""Validación, normalización y formateo de RUT chileno (dígito verificador módulo 11).

Este util lo crea EPIC-01 y lo importan las demás épicas. El RUT normalizado
(sin puntos ni guion, DV en mayúscula) es la forma canónica que se persiste.
"""

import re


class RutInvalidoError(ValueError):
    """Se lanza cuando un RUT no supera la validación de dígito verificador."""


_LIMPIEZA = re.compile(r"[.\-\s]")


def _calcular_dv(cuerpo: str) -> str:
    """Calcula el dígito verificador (módulo 11) de un cuerpo numérico de RUT."""
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def _separar(rut: str) -> tuple[str, str] | None:
    """Devuelve (cuerpo, dv_mayuscula) limpio, o None si el formato es inválido."""
    if not rut:
        return None
    limpio = _LIMPIEZA.sub("", rut).upper()
    if len(limpio) < 2:
        return None
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return None
    if not (dv.isdigit() or dv == "K"):
        return None
    return cuerpo, dv


def validar_rut(rut: str) -> bool:
    """True si el RUT es válido (dígito verificador correcto)."""
    partes = _separar(rut)
    if partes is None:
        return False
    cuerpo, dv = partes
    return _calcular_dv(cuerpo) == dv


def normalizar_rut(rut: str) -> str:
    """Devuelve la forma canónica `<cuerpo><DV>` (sin puntos ni guion, DV en mayúscula).

    Lanza RutInvalidoError si el RUT no es válido.
    """
    partes = _separar(rut)
    if partes is None or _calcular_dv(partes[0]) != partes[1]:
        raise RutInvalidoError(f"RUT inválido: {rut!r}")
    cuerpo, dv = partes
    return f"{cuerpo}{dv}"


def formatear_rut(rut: str) -> str:
    """Devuelve el RUT con puntos de miles y guion: `12.345.678-5`.

    Acepta tanto la forma canónica como una con separadores.
    """
    partes = _separar(rut)
    if partes is None:
        raise RutInvalidoError(f"RUT inválido: {rut!r}")
    cuerpo, dv = partes
    miles = f"{int(cuerpo):,}".replace(",", ".")
    return f"{miles}-{dv}"
