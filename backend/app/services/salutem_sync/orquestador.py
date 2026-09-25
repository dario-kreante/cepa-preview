"""Ejecuta un modo del sync: bandera, credenciales, lease, bitácora y errores.

Códigos de salida (los usa el cron):
    0 = terminó (ok, con errores de días puntuales, apagado u omitido por lease)
    1 = error (la ejecución quedó registrada con estado `error`)
    2 = SALUTEM sin credenciales configuradas
    3 = un modo manual (`vincular`, `backfill`) omitido por lease: no hizo nada
"""

import logging
import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.salutem.client import SalutemStubClient
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.salutem_sync import SalutemSyncEjecucion
from app.services.salutem_sync.backfill import DIAS_FUTURO, ejecutar_backfill
from app.services.salutem_sync.bitacora import abrir_ejecucion, cerrar_ejecucion, registrar_omitida
from app.services.salutem_sync.incremental import (
    hoy_en_santiago,
    ventana_caliente,
    ventana_fria,
    ventana_tibia,
)
from app.services.salutem_sync.lease import soltar_lease, tomar_lease
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import MODOS, Contadores
from app.services.salutem_sync.vinculacion import vincular

log = logging.getLogger("salutem_sync")

_VINCULAN_TODO = ("backfill", "fria")
# Modos que no están en el cron: los corre una persona, que tiene que enterarse si no
# hicieron nada porque otro proceso tenía el lease. Para el cron, omitir es normal (0).
MANUALES = ("vincular", "backfill")
OMITIDO = 3


class LeasePerdidoError(RuntimeError):
    """Otro proceso tomó el lease (este tardó más que su vigencia sin renovarlo)."""


@dataclass
class Opciones:
    desde: date | None = None
    verificar: bool = True
    dias_futuro: int = DIAS_FUTURO
    dias_vacios_para_parar: int = 365
    vincular_todo: bool = False


def correr(
    modo: str,
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    *,
    ahora: Callable[[], datetime],
    habilitado: bool,
    opciones: Opciones | None = None,
    dueno: str | None = None,
) -> int:
    if modo not in MODOS:
        raise ValueError(f"Modo desconocido: {modo!r}")
    opciones = opciones or Opciones()
    if not habilitado:
        log.info("Sync SALUTEM deshabilitado (SALUTEM_SYNC_HABILITADO=false); modo %s no se ejecuta", modo)
        return 0
    if modo != "vincular" and isinstance(cliente, SalutemStubClient):
        log.error("SALUTEM sin credenciales (SALUTEM_EMPRESA / SALUTEM_API_KEY): no se sincroniza")
        return 2

    dueno = dueno or f"{socket.gethostname()}:{os.getpid()}:{modo}"
    inicio = ahora()
    if not tomar_lease(db, dueno, inicio):
        log.info("Modo %s omitido: otro proceso tiene el lease", modo)
        registrar_omitida(db, modo, inicio)
        return OMITIDO if modo in MANUALES else 0

    def renovar() -> None:
        if not tomar_lease(db, dueno, ahora()):
            raise LeasePerdidoError(f"El lease dejó de pertenecer a {dueno}")

    ejecucion = None
    try:
        ingresos_desde = _ultimo_inicio_exitoso(db)
        ejecucion = abrir_ejecucion(db, modo, inicio)
        contadores, errores = _ejecutar_modo(modo, db, cliente, ritmo, inicio, opciones, renovar)
        vinculacion = vincular(
            db,
            ahora(),
            todo=modo in _VINCULAN_TODO or (modo == "vincular" and opciones.vincular_todo),
            ingresos_desde=ingresos_desde,
            al_avanzar=renovar,
        )
        errores = errores + vinculacion.errores
        log.info("Modo %s terminado: %s, vinculación %s", modo, contadores, vinculacion)
        # Si otro proceso tomó el lease, esta corrida pudo pisarse con la suya: no es `ok`.
        renovar()
        cerrar_ejecucion(
            db,
            ejecucion,
            estado="con_errores" if errores else "ok",
            ahora=ahora(),
            llamadas=ritmo.llamadas,
            contadores=contadores,
            error="; ".join(errores) if errores else None,
        )
        return 0
    except Exception as e:  # noqa: BLE001 — cualquier falla debe quedar en la bitácora
        log.exception("Modo %s falló", modo)
        # Si la base misma está caída, registrar el error también falla: se loguea y
        # el código de salida igual informa el error al cron.
        try:
            db.rollback()
            if ejecucion is not None:
                cerrar_ejecucion(
                    db, ejecucion, estado="error", ahora=ahora(),
                    llamadas=ritmo.llamadas, error=f"{type(e).__name__}: {e}",
                )
        except Exception:  # noqa: BLE001
            log.exception("No se pudo registrar el error del modo %s en la bitácora", modo)
        return 1
    finally:
        try:
            soltar_lease(db, dueno)
        except Exception:  # noqa: BLE001 — el lease vence solo al cabo de DURACION
            log.exception("No se pudo soltar el lease de %s", dueno)


def _ejecutar_modo(
    modo: str,
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    inicio: datetime,
    opciones: Opciones,
    renovar: Callable[[], None],
) -> tuple[Contadores, list[str]]:
    if modo == "vincular":
        return Contadores(), []
    if modo == "backfill":
        r = ejecutar_backfill(
            db, cliente, ritmo,
            hoy=hoy_en_santiago(inicio), ahora=inicio, desde=opciones.desde,
            dias_vacios_para_parar=opciones.dias_vacios_para_parar,
            dias_futuro=opciones.dias_futuro, verificar=opciones.verificar,
            al_terminar_dia=renovar,
        )
        log.info(
            "Backfill: %d días barridos, primer día con datos %s, %d atenciones recuperadas",
            r.dias_barridos, r.primer_dia_con_datos, r.atenciones_recuperadas,
        )
        if r.atenciones_anteriores:
            log.warning(
                "%d atenciones son anteriores al primer día barrido (%s): re-ejecutar con --desde más antiguo",
                r.atenciones_anteriores, r.primer_dia_barrido,
            )
        return r.contadores, r.errores
    ventana = {"caliente": ventana_caliente, "tibia": ventana_tibia, "fria": ventana_fria}[modo]
    r = ventana(db, cliente, ritmo, inicio, al_terminar_dia=renovar)
    return r.contadores, r.errores


def _ultimo_inicio_exitoso(db: Session) -> datetime | None:
    return db.scalar(
        select(func.max(SalutemSyncEjecucion.inicio)).where(
            SalutemSyncEjecucion.estado.in_(("ok", "con_errores"))
        )
    )
