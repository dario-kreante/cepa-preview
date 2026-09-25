"""Búsqueda 360° de pacientes (CEPA-012).

Criterios: RUT (normalizado), nombre (parcial, case-insensitive), folio y la
identidad en SALUTEM de los pacientes sin RUT (el `sin_id_…` que muestra SALUTEM o
el id interno de persona). La búsqueda nunca lanza error por término inexistente:
devuelve lista vacía (RN-5).
"""

import re

from sqlalchemy import func, select

from app.models.control_medico import ControlMedico
from app.models.farmacos import EsquemaIndicacion, Receta, RegistroFarmacologico
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.reintegro import CasoReintegro
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemPersona
from app.util.rut import RutInvalidoError, normalizar_rut

_SIN_ID = re.compile(r"^sin_id_\d+$", re.IGNORECASE)


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

    # 4) por identidad SALUTEM (pacientes sin RUT asociados por salutem_persona_id)
    ids |= _por_identidad_salutem(db, q)

    if not ids:
        return []
    return list(
        db.execute(
            select(Paciente).where(Paciente.id.in_(ids)).order_by(Paciente.nombre)
        ).scalars()
    )


def _por_identidad_salutem(db, q: str) -> set[int]:
    if q.isdigit():
        personas = {int(q)}
    elif _SIN_ID.match(q):
        # El sin_id es la "identificacion" que SALUTEM muestra y vive en el contenido
        # JSON (CLOB en Oracle): se compara en Python. Solo se revisan las personas
        # sin RUT, que son pocas.
        buscado = q.lower()
        personas = {
            p.salutem_id
            for p in db.scalars(select(SalutemPersona).where(SalutemPersona.rut.is_(None)))
            if str(p.contenido.get("identificacion") or "").lower() == buscado
        }
    else:
        return set()
    if not personas:
        return set()
    return set(
        db.scalars(select(Paciente.id).where(Paciente.salutem_persona_id.in_(personas)))
    )


def obtener_paciente(db, paciente_id: int) -> Paciente | None:
    return db.get(Paciente, paciente_id)


def vista_360(db, paciente: Paciente) -> dict:
    """Consolida el paciente, sus ingresos y los módulos de cada ingreso (CEPA-012).

    Una consulta por dimensión filtrada por los ingresos del paciente (sin N+1).
    """
    ingresos = list(
        db.execute(
            select(Ingreso).where(Ingreso.paciente_id == paciente.id).order_by(Ingreso.id)
        ).scalars()
    )
    vacio = {"farmacos": [], "licencias": [], "controles": [], "reintegro": []}
    if not ingresos:
        return {"paciente": paciente, "ingresos": ingresos, **vacio}
    ids = [i.id for i in ingresos]

    licencias = list(
        db.scalars(
            select(LicenciaMedica)
            .where(LicenciaMedica.ingreso_id.in_(ids))
            .order_by(LicenciaMedica.fecha_inicio, LicenciaMedica.id)
        )
    )
    controles = list(
        db.scalars(
            select(ControlMedico)
            .where(ControlMedico.ingreso_id.in_(ids))
            .order_by(ControlMedico.fecha_control, ControlMedico.id)
        )
    )
    reintegro = list(
        db.scalars(
            select(CasoReintegro)
            .where(CasoReintegro.ingreso_id.in_(ids))
            .order_by(CasoReintegro.fecha_caso, CasoReintegro.id)
        )
    )
    return {
        "paciente": paciente,
        "ingresos": ingresos,
        "farmacos": _farmacos_por_ingresos(db, ids),
        "licencias": licencias,
        "controles": controles,
        "reintegro": reintegro,
    }


def _farmacos_por_ingresos(db, ingreso_ids: list[int]) -> list[dict]:
    """Registros farmacológicos con indicaciones y recetas: tres consultas en total."""
    registros = list(
        db.scalars(
            select(RegistroFarmacologico)
            .where(RegistroFarmacologico.ingreso_id.in_(ingreso_ids))
            .order_by(RegistroFarmacologico.id)
        )
    )
    if not registros:
        return []
    reg_ids = [r.id for r in registros]
    indicaciones: dict[int, list] = {r: [] for r in reg_ids}
    for ind in db.scalars(
        select(EsquemaIndicacion)
        .where(EsquemaIndicacion.registro_id.in_(reg_ids))
        .order_by(EsquemaIndicacion.id)
    ):
        indicaciones[ind.registro_id].append(ind)
    recetas: dict[int, list] = {r: [] for r in reg_ids}
    for rec in db.scalars(
        select(Receta).where(Receta.registro_id.in_(reg_ids)).order_by(Receta.id)
    ):
        recetas[rec.registro_id].append(rec)
    return [
        {
            "id": r.id,
            "ingreso_id": r.ingreso_id,
            "medico_tratante": r.medico_tratante,
            "estado_farmacologico": r.estado_farmacologico,
            "antecedentes_previos": r.antecedentes_previos,
            "tratamiento_previo": r.tratamiento_previo,
            "activo": r.activo,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "indicaciones": indicaciones[r.id],
            "recetas": recetas[r.id],
        }
        for r in registros
    ]
