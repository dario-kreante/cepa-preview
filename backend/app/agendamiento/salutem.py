"""Cruce de pacientes del CEPA con la copia de SALUTEM (solo lectura)."""

from collections.abc import Collection
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemCita, SalutemPersona
from app.services.salutem_sync.filtro import cruce_con_paciente
from app.services.salutem_sync.vigencia import cita_vigente_desde

_LOTE = 500  # Oracle limita a 1000 elementos en un IN


def _lotes(ids: Collection[int]):
    lista = list(ids)
    for i in range(0, len(lista), _LOTE):
        yield lista[i : i + _LOTE]


def pacientes_con_hora_vigente(db: Session, paciente_ids: Collection[int], hoy: date) -> set[int]:
    """Pacientes con una cita vigente desde `hoy` en SALUTEM (cruce por RUT o persona_id)."""
    encontrados: set[int] = set()
    for lote in _lotes(paciente_ids):
        encontrados.update(
            db.scalars(
                select(Paciente.id)
                .join(SalutemPersona, cruce_con_paciente())
                .join(SalutemCita, SalutemCita.persona_id == SalutemPersona.salutem_id)
                .where(Paciente.id.in_(lote), cita_vigente_desde(hoy))
                .distinct()
            )
        )
    return encontrados


def pacientes_sin_vinculo(db: Session, paciente_ids: Collection[int]) -> set[int]:
    """Pacientes sin ninguna persona de SALUTEM que cruce con ellos."""
    con_vinculo: set[int] = set()
    for lote in _lotes(paciente_ids):
        con_vinculo.update(
            db.scalars(
                select(Paciente.id)
                .join(SalutemPersona, cruce_con_paciente())
                .where(Paciente.id.in_(lote))
                .distinct()
            )
        )
    return set(paciente_ids) - con_vinculo
