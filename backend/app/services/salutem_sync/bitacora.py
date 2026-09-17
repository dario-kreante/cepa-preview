"""Bitácora de ejecuciones del sync (tabla salutem_sync_ejecucion)."""

from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.salutem_sync import SalutemSyncEjecucion
from app.services.salutem_sync.lease import DURACION
from app.services.salutem_sync.tipos import Contadores, a_utc

_MAX_ERROR = 2000
_ABANDONADA = "Ejecución abandonada (proceso terminado sin cerrar)"


def abrir_ejecucion(db: Session, modo: str, ahora: datetime) -> SalutemSyncEjecucion:
    """Abre la ejecución y cierra como `error` las que quedaron `en_curso` de un proceso muerto.

    Quien abre tiene el lease, y un proceso vivo lo renueva: una `en_curso` más antigua
    que la vigencia del lease ya no tiene dueño que la cierre.
    """
    ahora = a_utc(ahora)
    db.execute(
        update(SalutemSyncEjecucion)
        .where(SalutemSyncEjecucion.estado == "en_curso", SalutemSyncEjecucion.inicio < ahora - DURACION)
        .values(estado="error", fin=ahora, error=_ABANDONADA)
        .execution_options(synchronize_session=False)
    )
    ejecucion = SalutemSyncEjecucion(
        modo=modo, estado="en_curso", inicio=ahora,
        llamadas=0, nuevos=0, cambiados=0, desaparecidos=0,
    )
    db.add(ejecucion)
    db.commit()
    return ejecucion


def cerrar_ejecucion(
    db: Session,
    ejecucion: SalutemSyncEjecucion,
    *,
    estado: str,
    ahora: datetime,
    llamadas: int = 0,
    contadores: Contadores | None = None,
    error: str | None = None,
) -> None:
    contadores = contadores or Contadores()
    ahora = a_utc(ahora)
    ejecucion.estado = estado
    ejecucion.fin = ahora
    ejecucion.llamadas = llamadas
    ejecucion.nuevos = contadores.nuevos
    ejecucion.cambiados = contadores.cambiados
    ejecucion.desaparecidos = contadores.desaparecidos
    ejecucion.error = error[:_MAX_ERROR] if error else None
    db.commit()


def registrar_omitida(db: Session, modo: str, ahora: datetime) -> SalutemSyncEjecucion:
    """Otro proceso tenía el lease: se deja constancia y no se hace nada."""
    ahora = a_utc(ahora)
    ejecucion = SalutemSyncEjecucion(
        modo=modo, estado="omitida", inicio=ahora, fin=ahora,
        llamadas=0, nuevos=0, cambiados=0, desaparecidos=0,
    )
    db.add(ejecucion)
    db.commit()
    return ejecucion
