"""Gestión de contacto con pacientes por citar: bitácora de intentos y consultas derivadas.

SQL portable a Postgres y Oracle 19c: sin DISTINCT ON ni funciones de ventana; las listas IN se
parten en lotes de 500 (límite de 1000 de Oracle). Los servicios solo hacen flush; commit en el router.
"""

from collections.abc import Collection
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agendamiento.enums import ResultadoGestion
from app.agendamiento.models import GestionCitacion
from app.agendamiento.salutem import _lotes
from app.audit.service import record_audit
from app.models.paciente import Paciente
from app.models.profesional import Profesional


def registrar_gestion(
    db: Session,
    paciente_id: int,
    profesional_id: int,
    resultado: ResultadoGestion,
    nota: str | None,
    actor: str,
    rol: str,
) -> GestionCitacion:
    if db.get(Paciente, paciente_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    if db.get(Profesional, profesional_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesional no encontrado")
    g = GestionCitacion(
        paciente_id=paciente_id,
        profesional_id=profesional_id,
        resultado=resultado.value,
        nota=nota,
        usuario=actor,
    )
    db.add(g)
    db.flush()
    record_audit(
        db, actor=actor, rol=rol, action="CREATE", entity="gestion_citacion",
        entity_id=str(g.id), valor_nuevo=resultado.value,
    )
    return g


def listar_gestiones(db: Session, paciente_id: int) -> list[GestionCitacion]:
    """De la más reciente a la más antigua (el id desempata)."""
    return list(db.scalars(
        select(GestionCitacion)
        .where(GestionCitacion.paciente_id == paciente_id)
        .order_by(GestionCitacion.created_at.desc(), GestionCitacion.id.desc())
    ))


def ultimas_gestiones(db: Session, paciente_ids: Collection[int]) -> dict[int, GestionCitacion]:
    """La última gestión de cada paciente (con cualquier profesional). Ante empate, el id mayor."""
    resultado: dict[int, GestionCitacion] = {}
    for lote in _lotes(paciente_ids):
        maximo = (
            select(
                GestionCitacion.paciente_id.label("paciente_id"),
                func.max(GestionCitacion.created_at).label("max_creado"),
            )
            .where(GestionCitacion.paciente_id.in_(lote))
            .group_by(GestionCitacion.paciente_id)
            .subquery()
        )
        filas = db.scalars(
            select(GestionCitacion)
            .join(
                maximo,
                (GestionCitacion.paciente_id == maximo.c.paciente_id)
                & (GestionCitacion.created_at == maximo.c.max_creado),
            )
            .order_by(GestionCitacion.id)
        )
        for g in filas:  # ordenadas por id: la última escritura por paciente es el id mayor
            resultado[g.paciente_id] = g
    return resultado


def ocultos_por_agendada(
    db: Session, profesional_id: int, paciente_ids: Collection[int], desde: datetime
) -> set[int]:
    """Pacientes con una gestión 'agendada_en_salutem' de ese profesional desde `desde`."""
    ocultos: set[int] = set()
    for lote in _lotes(paciente_ids):
        ocultos.update(db.scalars(
            select(GestionCitacion.paciente_id)
            .where(
                GestionCitacion.paciente_id.in_(lote),
                GestionCitacion.profesional_id == profesional_id,
                GestionCitacion.resultado == ResultadoGestion.AGENDADA_EN_SALUTEM.value,
                GestionCitacion.created_at >= desde,
            )
            .distinct()
        ))
    return ocultos


def ultima_gestion_por_profesional(
    db: Session, profesional_id: int, paciente_ids: Collection[int]
) -> dict[int, GestionCitacion]:
    """La última gestión (cualquier resultado) de cada paciente con ESE profesional.

    Ante empate de created_at gana el id mayor. Portable: máximo por subconsulta, sin DISTINCT ON.
    """
    resultado: dict[int, GestionCitacion] = {}
    for lote in _lotes(paciente_ids):
        maximo = (
            select(
                GestionCitacion.paciente_id.label("paciente_id"),
                func.max(GestionCitacion.created_at).label("max_creado"),
            )
            .where(
                GestionCitacion.paciente_id.in_(lote),
                GestionCitacion.profesional_id == profesional_id,
            )
            .group_by(GestionCitacion.paciente_id)
            .subquery()
        )
        filas = db.scalars(
            select(GestionCitacion)
            .join(
                maximo,
                (GestionCitacion.paciente_id == maximo.c.paciente_id)
                & (GestionCitacion.created_at == maximo.c.max_creado),
            )
            .where(GestionCitacion.profesional_id == profesional_id)
            .order_by(GestionCitacion.id)
        )
        for g in filas:  # ordenadas por id: la última escritura por paciente es el id mayor
            resultado[g.paciente_id] = g
    return resultado
