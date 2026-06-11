"""Servicio de alertas de vencimiento de licencias médicas — CEPA-072.

contar_dias_habiles(desde, hasta): cuenta días hábiles (lun–vie) entre dos fechas,
  excluyendo fines de semana. Los festivos chilenos se gestionan como lista
  configurable (ver Notas de cierre del plan); por defecto esta función solo
  excluye sáb/dom para mantener el servicio portable y sin dependencia externa.

generar_alertas_vencimiento(db, hoy, umbral_habiles=3): idempotente — por cada LM
  vigente que vence en ≤umbral_habiles días hábiles, crea una AlertaLicencia solo
  si no existe ya una activa para esa LM (RN-4 CEPA-072).
"""

import datetime

from sqlalchemy import select

from app.models.alerta_licencia import AlertaLicencia
from app.models.licencia import LicenciaMedica


def contar_dias_habiles(
    desde: datetime.date,
    hasta: datetime.date,
    festivos: frozenset[datetime.date] | None = None,
) -> int:
    """Cuenta los días hábiles entre `desde` (exclusivo) y `hasta` (inclusivo).

    Un día hábil es lunes-viernes y no está en `festivos`.
    Devuelve valor negativo si `hasta` < `desde` (LM vencida).
    """
    festivos = festivos or frozenset()
    if hasta < desde:
        # calcular negativo para indicar que ya venció
        return -contar_dias_habiles(hasta, desde, festivos)
    conteo = 0
    cursor = desde + datetime.timedelta(days=1)
    while cursor <= hasta:
        if cursor.weekday() < 5 and cursor not in festivos:  # 0=lun, 4=vie
            conteo += 1
        cursor += datetime.timedelta(days=1)
    return conteo


def generar_alertas_vencimiento(
    db,
    hoy: datetime.date | None = None,
    umbral_habiles: int = 3,
    festivos: frozenset[datetime.date] | None = None,
) -> list[AlertaLicencia]:
    """Genera alertas in-app para LM que vencen en ≤umbral_habiles días hábiles.

    Idempotente: no crea alerta si ya existe una activa para la misma licencia_id.
    Excluye LM anuladas y LM cuya fecha_termino < hoy (ya vencidas).
    Devuelve la lista de alertas NUEVAS creadas en esta ejecución.
    """
    hoy = hoy or datetime.date.today()
    festivos = festivos or frozenset()

    # LM vigentes cuyo término es >= hoy (no vencidas aún)
    lm_candidatas = list(
        db.scalars(
            select(LicenciaMedica).where(
                LicenciaMedica.anulada.is_(False),
                LicenciaMedica.fecha_termino >= hoy,
            )
        )
    )

    nuevas: list[AlertaLicencia] = []
    for lm in lm_candidatas:
        habiles = contar_dias_habiles(hoy, lm.fecha_termino, festivos)
        if habiles > umbral_habiles:
            continue  # todavía no está en la ventana de alerta

        # Idempotencia: ¿ya existe una alerta activa para esta LM?
        existente = db.execute(
            select(AlertaLicencia).where(
                AlertaLicencia.licencia_id == lm.id,
                AlertaLicencia.activa.is_(True),
            )
        ).scalar_one_or_none()
        if existente is not None:
            continue

        alerta = AlertaLicencia(
            licencia_id=lm.id,
            ingreso_id=lm.ingreso_id,
            fecha_termino_lm=lm.fecha_termino,
            dias_habiles_restantes=habiles,
            activa=True,
        )
        db.add(alerta)
        nuevas.append(alerta)

    if nuevas:
        db.flush()
    return nuevas
