"""Búsqueda 360° de pacientes (CEPA-012).

Criterios: RUT (normalizado), nombre (parcial, case-insensitive) y folio. La
búsqueda nunca lanza error por término inexistente: devuelve lista vacía (RN-5).
"""

from sqlalchemy import func, select

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.util.rut import RutInvalidoError, normalizar_rut


def buscar_pacientes(db, q: str) -> list[Paciente]:
    """Devuelve pacientes que matchean por RUT exacto, nombre parcial o folio."""
    q = (q or "").strip()
    if not q:
        return []
    ids: set[int] = set()

    # 1) por RUT (si el término normaliza a un RUT válido)
    try:
        rut_norm = normalizar_rut(q)
        for p in db.execute(select(Paciente).where(Paciente.rut == rut_norm)).scalars():
            ids.add(p.id)
    except RutInvalidoError:
        pass

    # 2) por folio exacto -> paciente del ingreso
    for ing in db.execute(select(Ingreso).where(Ingreso.folio == q)).scalars():
        ids.add(ing.paciente_id)

    # 3) por nombre parcial (case-insensitive, portable con lower())
    patron = f"%{q.lower()}%"
    for p in db.execute(
        select(Paciente).where(func.lower(Paciente.nombre).like(patron))
    ).scalars():
        ids.add(p.id)

    if not ids:
        return []
    return list(
        db.execute(
            select(Paciente).where(Paciente.id.in_(ids)).order_by(Paciente.nombre)
        ).scalars()
    )


def obtener_paciente(db, paciente_id: int) -> Paciente | None:
    return db.get(Paciente, paciente_id)


def vista_360(db, paciente: Paciente) -> dict:
    """Consolida los ingresos del paciente. Otras dimensiones quedan como ranuras."""
    ingresos = list(
        db.execute(
            select(Ingreso).where(Ingreso.paciente_id == paciente.id).order_by(Ingreso.id)
        ).scalars()
    )
    return {
        "paciente": paciente,
        "ingresos": ingresos,
        "farmacos": [],
        "licencias": [],
        "controles": [],
        "reintegro": [],
    }
