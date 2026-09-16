"""Bitácora de ejecuciones del sync (tabla salutem_sync_ejecucion)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.salutem_sync import SalutemSyncEjecucion
from app.services.salutem_sync.tipos import Contadores

_MAX_ERROR = 2000


def abrir_ejecucion(db: Session, modo: str, ahora: datetime) -> SalutemSyncEjecucion:
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
    ejecucion = SalutemSyncEjecucion(
        modo=modo, estado="omitida", inicio=ahora, fin=ahora,
        llamadas=0, nuevos=0, cambiados=0, desaparecidos=0,
    )
    db.add(ejecucion)
    db.commit()
    return ejecucion
