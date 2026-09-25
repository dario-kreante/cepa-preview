"""Lectura de la configuración de alertas y de los festivos — COMP-2609-07.

Se consulta en cada ejecución del job (no se cachea): un cambio de Coordinación aplica en
la siguiente corrida sin reiniciar la API ni el cron (TC-072-07).
Si la tabla está vacía o le falta un tipo, se usan los valores de ``VENTANAS_DEFAULT``.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.config_alerta import ConfigAlerta, Festivo


def cargar_ventanas(db: Session) -> dict[str, dict]:
    """Devuelve {tipo: {"dias", "habiles", "activo"}} para todos los tipos del motor."""
    from app.services.alertas import VENTANAS_DEFAULT

    ventanas = {
        tipo: {"dias": v["dias"], "habiles": v["habiles"], "activo": v.get("activo", True)}
        for tipo, v in VENTANAS_DEFAULT.items()
    }
    for fila in db.scalars(select(ConfigAlerta)):
        if fila.tipo in ventanas:
            ventanas[fila.tipo] = {
                "dias": fila.dias,
                "habiles": bool(fila.habiles),
                "activo": bool(fila.activo),
            }
    return ventanas


def cargar_festivos(db: Session) -> frozenset[date]:
    return frozenset(db.scalars(select(Festivo.fecha)))
