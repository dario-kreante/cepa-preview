"""Fármacos sugeridos desde las atenciones de SALUTEM ya importadas.

El médico escribe la receta como texto en una indicación "Receta Medicamentos".
Este servicio la estructura (medicamento, dosis, frecuencia) y la propone para que
un administrativo la revise y la agregue al esquema o registre la receta. No
escribe nada: ni en el CEPA ni en SALUTEM (D12).
"""

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.farmacos import extraer_farmacos
from app.models.farmacos import EsquemaIndicacion, Receta, RegistroFarmacologico
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.schemas.farmaco_sugerido import FarmacoSugeridoRead


def _fecha_cita(valor: Any) -> date | None:
    if not isinstance(valor, str):
        return None
    try:
        return date.fromisoformat(valor[:10])
    except ValueError:
        return None


def _es_receta(indicacion: Any) -> bool:
    if not isinstance(indicacion, dict):
        return False
    # SALUTEM separa por tipo: "Receta Medicamentos" (con nombre "Receta" o
    # "Indicaciones de tratamiento farmacológico"), "Indicación", "Documento"...
    return "receta" in str(indicacion.get("tipo") or "").casefold()


def _recetas(contenido: dict[str, Any]) -> list[Any]:
    indicaciones = contenido.get("indicaciones") or []
    if isinstance(indicaciones, dict):
        indicaciones = [indicaciones]
    return [i.get("registro") for i in indicaciones if _es_receta(i)]


def _clave(texto: str) -> str:
    return " ".join(texto.casefold().split())


def sugerir_farmacos(db: Session, ingreso_id: int) -> list[FarmacoSugeridoRead]:
    if db.get(Ingreso, ingreso_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe el ingreso {ingreso_id}.")
    fichas = db.scalars(
        select(FichaClinica).where(
            FichaClinica.ingreso_id == ingreso_id,
            FichaClinica.origen == "SALUTEM",
            FichaClinica.eliminada_en_origen.is_(None),
        )
    ).all()

    registro = db.scalar(
        select(RegistroFarmacologico).where(RegistroFarmacologico.ingreso_id == ingreso_id)
    )
    en_esquema: set[tuple[str, str]] = set()
    recetas: list[Receta] = []
    if registro is not None:
        en_esquema = {
            (_clave(i.medicamento), _clave(i.dosis))
            for i in db.scalars(
                select(EsquemaIndicacion).where(EsquemaIndicacion.registro_id == registro.id)
            )
            if i.vigente
        }
        recetas = list(db.scalars(select(Receta).where(Receta.registro_id == registro.id)))

    # Un mismo medicamento se receta en muchos controles: se sugiere una vez, con la
    # atención más reciente que lo menciona.
    por_clave: dict[tuple[str, str, str], FarmacoSugeridoRead] = {}
    for ficha in fichas:
        contenido = ficha.contenido or {}
        fecha = _fecha_cita(contenido.get("citaFecha"))
        if fecha is None:
            continue
        profesional = contenido.get("profesionalNombre")
        for registro_receta in _recetas(contenido):
            for m in extraer_farmacos(registro_receta):
                clave = (_clave(m.medicamento), _clave(m.dosis), m.frecuencia.value)
                previa = por_clave.get(clave)
                if previa is not None and previa.cita_fecha >= fecha:
                    continue
                med = _clave(m.medicamento)
                por_clave[clave] = FarmacoSugeridoRead(
                    ficha_clinica_id=ficha.id,
                    cita_fecha=fecha,
                    profesional=profesional if isinstance(profesional, str) else None,
                    texto=m.texto,
                    medicamento=m.medicamento,
                    dosis=m.dosis,
                    frecuencia=m.frecuencia,
                    avisos=list(m.avisos),
                    en_esquema=(med, _clave(m.dosis)) in en_esquema,
                    receta_registrada=any(
                        r.fecha_emision == fecha and med in _clave(r.marca_medicamento)
                        for r in recetas
                    ),
                )
    return sorted(por_clave.values(), key=lambda s: (s.cita_fecha, s.medicamento), reverse=True)
