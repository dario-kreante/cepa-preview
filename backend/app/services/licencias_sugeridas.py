"""Licencias sugeridas desde las atenciones de SALUTEM ya importadas.

SALUTEM no tiene licencias estructuradas: el médico las escribe en las
indicaciones. Este servicio las lee con el extractor y las propone para que un
administrativo las revise y registre. No escribe nada: ni en el CEPA ni en
SALUTEM (D12).
"""

from datetime import date
from typing import Any

from sqlalchemy import false, select
from sqlalchemy.orm import Session

from app.domain.enums_licencia import OrigenLicencia, TipoLicencia, TipoReposo
from app.integrations.salutem.licencias import ClaseMencion, MencionLicencia, extraer_licencia
from app.models.ficha_clinica import FichaClinica
from app.models.licencia import LicenciaMedica
from app.schemas.licencia_sugerida import LicenciaSugeridaRead
from app.services.ficha_clinica import _obtener_ingreso_por_folio

_TIPOS_CATALOGO = sorted(t.value for t in TipoLicencia)


def _fecha_cita(valor: Any) -> date | None:
    if not isinstance(valor, str):
        return None
    try:
        return date.fromisoformat(valor[:10])
    except ValueError:
        return None


def _registros(contenido: dict[str, Any]) -> list[Any]:
    indicaciones = contenido.get("indicaciones") or []
    if isinstance(indicaciones, dict):
        indicaciones = [indicaciones]
    return [i.get("registro") if isinstance(i, dict) else i for i in indicaciones]


def _ya_registrada(mencion: MencionLicencia, registradas: list[LicenciaMedica]) -> bool:
    """Una licencia se reconoce por su fecha de inicio; sin inicio, por la de término."""
    for lm in registradas:
        if mencion.fecha_inicio is not None:
            if lm.fecha_inicio == mencion.fecha_inicio:
                return True
        elif mencion.fecha_termino is not None and lm.fecha_termino == mencion.fecha_termino:
            return True
    return False


def sugerir_licencias(db: Session, folio: str) -> list[LicenciaSugeridaRead]:
    ingreso = _obtener_ingreso_por_folio(db, folio)
    fichas = db.scalars(
        select(FichaClinica)
        .where(FichaClinica.folio == folio, FichaClinica.origen == "SALUTEM")
        .order_by(FichaClinica.id)
    ).all()
    registradas = list(
        db.scalars(
            select(LicenciaMedica).where(
                # `== false()` y no `.is_(False)`: Oracle rechaza "IS 0" (ORA-00908).
                LicenciaMedica.ingreso_id == ingreso.id, LicenciaMedica.anulada == false()
            )
        ).all()
    )

    sugerencias: list[LicenciaSugeridaRead] = []
    vistas: set[tuple] = set()
    for ficha in fichas:
        contenido = ficha.contenido or {}
        fecha = _fecha_cita(contenido.get("citaFecha"))
        if fecha is None:
            continue
        for registro in _registros(contenido):
            mencion = extraer_licencia(registro, fecha_atencion=fecha)
            if mencion is None or mencion.clase != ClaseMencion.LICENCIA:
                continue
            # El médico suele repetir la misma licencia en varias indicaciones.
            clave = (
                mencion.fecha_inicio,
                mencion.fecha_termino,
                mencion.tipo_licencia,
                mencion.extra_sistema,
            )
            if clave in vistas:
                continue
            vistas.add(clave)

            avisos = list(mencion.avisos)
            tipo = mencion.tipo_licencia
            if tipo is not None and tipo not in _TIPOS_CATALOGO:
                avisos.append(
                    f"El tipo de licencia {tipo} no está en el catálogo del CEPA "
                    f"({', '.join(_TIPOS_CATALOGO)}): elige el tipo al registrarla."
                )
                tipo = None

            sugerencias.append(
                LicenciaSugeridaRead(
                    ficha_clinica_id=ficha.id,
                    cita_fecha=fecha,
                    texto=mencion.texto,
                    tipo_lm=TipoLicencia(tipo) if tipo else None,
                    tipo_reposo=TipoReposo(mencion.tipo_reposo) if mencion.tipo_reposo else None,
                    origen=(
                        OrigenLicencia.EXTRA_SISTEMA
                        if mencion.extra_sistema
                        else OrigenLicencia.SISTEMA
                    ),
                    fecha_inicio=mencion.fecha_inicio,
                    fecha_termino=mencion.fecha_termino,
                    termino_calculado=mencion.termino_calculado,
                    cantidad_dias=mencion.dias,
                    avisos=avisos,
                    ya_registrada=_ya_registrada(mencion, registradas),
                )
            )
    return sugerencias
