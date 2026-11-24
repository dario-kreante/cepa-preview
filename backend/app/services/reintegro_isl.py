"""Paciente ISL y fecha de envío del caso EPT, para los plazos de reintegro (QA-010, 23-11-2026).

«Propongo que sean 15 días corridos desde la fecha de envío de caso (que se genera en EPT), y
SÓLO para los pacientes ISL, los del área clínica no tienen RECA.» (clienta, QA 23-11-2026)

- Paciente ISL: el ingreso tiene una derivación del flujo ISL (DIEP, «DIEP sin EPT», DIAT,
  «PAPT a flujo AT», «Reingreso ISL»), un programa que dice «ISL» o un caso EPT.
- Fecha de envío del caso: la fecha de envío real a ISL registrada en los plazos del caso EPT del
  ingreso (``plazo_ept.fecha_envio``). Si el ingreso tiene varios casos EPT enviados, la primera.
  Sin envío registrado, la fecha del caso de reintegro.
"""

from datetime import date

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.orm import Session

from app.agendamiento.salutem import lotes
from app.domain.enums import TipoDerivacion
from app.models.ept import CasoEpt, PlazoEpt
from app.models.ingreso import Ingreso

DERIVACIONES_ISL = (
    TipoDerivacion.DIEP.value,
    TipoDerivacion.DIEP_SIN_EPT.value,
    TipoDerivacion.DIAT.value,
    TipoDerivacion.PAPT_FLUJO_AT.value,
    TipoDerivacion.REINGRESO_ISL.value,
)


def ingreso_es_isl() -> ColumnElement[bool]:
    """Condición SQL (sobre ``Ingreso``) de paciente ISL. Portable a Oracle."""
    return or_(
        Ingreso.tipo_derivacion.in_(DERIVACIONES_ISL),
        func.upper(Ingreso.programa).like("%ISL%"),
        exists().where(CasoEpt.ingreso_id == Ingreso.id),
    )


def ingresos_isl(db: Session, ingreso_ids: set[int]) -> set[int]:
    """De los ingresos dados, los que son de paciente ISL (por lotes, para el IN de Oracle)."""
    resultado: set[int] = set()
    for lote in lotes(ingreso_ids):
        resultado.update(db.scalars(select(Ingreso.id).where(Ingreso.id.in_(lote), ingreso_es_isl())))
    return resultado


def fechas_envio_ept(db: Session, ingreso_ids: set[int]) -> dict[int, date]:
    """Primera fecha de envío a ISL de los casos EPT de cada ingreso (solo los que la tienen)."""
    fechas: dict[int, date] = {}
    for lote in lotes(ingreso_ids):
        filas = db.execute(
            select(CasoEpt.ingreso_id, func.min(PlazoEpt.fecha_envio))
            .join(PlazoEpt, PlazoEpt.caso_ept_id == CasoEpt.id)
            .where(CasoEpt.ingreso_id.in_(lote), PlazoEpt.fecha_envio.is_not(None))
            .group_by(CasoEpt.ingreso_id)
        )
        fechas.update({ingreso_id: fecha for ingreso_id, fecha in filas})
    return fechas
