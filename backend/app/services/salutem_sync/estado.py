"""Estado del sync para el endpoint y el CLI."""

from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemCita, SalutemPersona
from app.models.salutem_sync import SalutemSyncEjecucion
from app.schemas.salutem_sync import EjecucionRead, EstadoSyncRead
from app.services.salutem_sync.tipos import MODOS, a_utc

MAX_ATRASO = timedelta(minutes=20)
EXITOSAS = ("ok", "con_errores")


def estado_sync(db: Session, ahora: datetime) -> EstadoSyncRead:
    ahora = a_utc(ahora)
    ultimas: dict[str, EjecucionRead] = {}
    for modo in MODOS:
        ejecucion = db.scalars(
            select(SalutemSyncEjecucion)
            .where(SalutemSyncEjecucion.modo == modo, SalutemSyncEjecucion.estado != "omitida")
            .order_by(SalutemSyncEjecucion.inicio.desc(), SalutemSyncEjecucion.id.desc())
            .limit(1)
        ).first()
        if ejecucion is not None:
            ultimas[modo] = EjecucionRead.model_validate(ejecucion)

    # Se compara en SQL: Oracle puede devolver los timestamps sin zona.
    calientes_recientes = db.scalar(
        select(func.count()).select_from(SalutemSyncEjecucion).where(
            SalutemSyncEjecucion.modo == "caliente",
            SalutemSyncEjecucion.estado.in_(EXITOSAS),
            SalutemSyncEjecucion.fin >= ahora - MAX_ATRASO,
        )
    )
    pendientes = db.scalar(
        select(func.count())
        .select_from(SalutemAtencion)
        .join(SalutemPersona, SalutemPersona.salutem_id == SalutemAtencion.persona_id)
        .join(Paciente, Paciente.rut == SalutemPersona.rut)
        .where(
            or_(
                SalutemAtencion.hash_vinculado.is_(None),
                SalutemAtencion.hash_vinculado != SalutemAtencion.hash_contenido,
            )
        )
    )
    return EstadoSyncRead(
        ultimas=ultimas,
        primer_dia_con_datos=db.scalar(select(func.min(SalutemCita.fecha_cita))),
        personas=db.scalar(select(func.count()).select_from(SalutemPersona)),
        citas=db.scalar(select(func.count()).select_from(SalutemCita)),
        atenciones=db.scalar(select(func.count()).select_from(SalutemAtencion)),
        atenciones_pendientes=pendientes,
        atrasado=calientes_recientes == 0,
    )
