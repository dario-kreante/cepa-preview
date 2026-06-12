"""Cálculo de días acumulados de licencias médicas por ingreso — CEPA-071.

Esta función es pura respecto a la BD (solo consulta, no muta) y está diseñada
para ser reutilizada por EPIC-12 (API de integración).

Algoritmo de días calendario efectivos (RN-3 CEPA-071):
  1. Filtrar LM vigentes (anulada=False) del ingreso.
  2. Para el bruto: sumar cantidad_dias directamente (suma simple).
  3. Para el efectivo: construir la unión de intervalos [fecha_inicio, fecha_termino]
     contando días de calendario únicos (set de fechas).
  4. Si el tamaño del set < suma bruta → hay solapamiento.
"""

import datetime
from dataclasses import dataclass

from sqlalchemy import select, false

from app.models.licencia import LicenciaMedica


@dataclass
class ResultadoAcumulado:
    ingreso_id: int
    dias_acumulados_vigentes: int
    dias_acumulados_bruto: int
    hay_solapamiento: bool
    incluye_extra_sistema: bool


def calcular_acumulado(db, ingreso_id: int) -> ResultadoAcumulado:
    """Calcula el acumulado de días de licencia para el ingreso dado.

    - dias_acumulados_bruto: suma de campo cantidad_dias de todas las LM vigentes.
    - dias_acumulados_vigentes: días calendario únicos en la unión de intervalos
      [fecha_inicio, fecha_termino] (evita doble-conteo de solapamientos).
    - hay_solapamiento: True si se detectaron intervalos superpuestos.
    - incluye_extra_sistema: True si al menos una LM es de origen extra_sistema.

    Las LM anuladas (anulada=True) se excluyen del cómputo vigente (RN-4 CEPA-071).
    """
    licencias = list(
        db.scalars(
            select(LicenciaMedica)
            .where(
                LicenciaMedica.ingreso_id == ingreso_id,
                LicenciaMedica.anulada == false(),
            )
            .order_by(LicenciaMedica.fecha_inicio)
        )
    )

    if not licencias:
        return ResultadoAcumulado(
            ingreso_id=ingreso_id,
            dias_acumulados_vigentes=0,
            dias_acumulados_bruto=0,
            hay_solapamiento=False,
            incluye_extra_sistema=False,
        )

    dias_bruto = sum(lm.cantidad_dias for lm in licencias)
    incluye_extra = any(lm.origen == "extra_sistema" for lm in licencias)

    # Unión de intervalos: set de fechas calendario cubiertas
    dias_calendario: set[datetime.date] = set()
    for lm in licencias:
        delta = (lm.fecha_termino - lm.fecha_inicio).days + 1
        for offset in range(delta):
            dias_calendario.add(lm.fecha_inicio + datetime.timedelta(days=offset))

    dias_efectivos = len(dias_calendario)
    hay_solapamiento = dias_efectivos < dias_bruto

    return ResultadoAcumulado(
        ingreso_id=ingreso_id,
        dias_acumulados_vigentes=dias_efectivos,
        dias_acumulados_bruto=dias_bruto,
        hay_solapamiento=hay_solapamiento,
        incluye_extra_sistema=incluye_extra,
    )
