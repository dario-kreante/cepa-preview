"""Lease en base de datos: un solo proceso de sync a la vez.

No usa SELECT FOR UPDATE: una carga inicial dura horas y mantener una
transacción abierta tanto tiempo en Oracle es frágil. El lease vence solo, así
que un proceso que muere lo libera al cabo de DURACION.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.models.salutem_sync import SalutemSyncLease
from app.services.salutem_sync.tipos import a_utc

NOMBRE = "salutem"
DURACION = timedelta(minutes=30)
_LIBRE = datetime(2000, 1, 1, tzinfo=timezone.utc)


def tomar_lease(
    db: Session, dueno: str, ahora: datetime, duracion: timedelta = DURACION
) -> bool:
    """Toma o renueva el lease. False si otro proceso lo tiene vigente. Confirma la transacción.

    `ahora` se normaliza a UTC (ver `a_utc`): con otro huso correría el lease.
    """
    ahora = a_utc(ahora)
    resultado = db.execute(
        update(SalutemSyncLease)
        .where(
            SalutemSyncLease.nombre == NOMBRE,
            or_(SalutemSyncLease.vence_en < ahora, SalutemSyncLease.dueno == dueno),
        )
        .values(dueno=dueno, vence_en=ahora + duracion)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return resultado.rowcount == 1


def soltar_lease(db: Session, dueno: str) -> None:
    db.execute(
        update(SalutemSyncLease)
        .where(SalutemSyncLease.nombre == NOMBRE, SalutemSyncLease.dueno == dueno)
        .values(dueno=None, vence_en=_LIBRE)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.expire_all()
