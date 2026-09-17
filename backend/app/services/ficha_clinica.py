"""Servicio de fichas clínicas — push/pull bidireccional (CEPA-121 CA-3).

D12: solo lectura hacia SALUTEM. La persistencia es siempre en el dominio CEPA.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.client import get_salutem_client
from app.integrations.salutem.errors import (
    SalutemError,
    SalutemRequestError,
    SalutemUnavailableError,
)
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.schemas.ficha_clinica import FichaClinicaCreate


def _obtener_ingreso_por_folio(db: Session, folio: str) -> Ingreso:
    ingreso = db.execute(
        select(Ingreso).where(Ingreso.folio == folio)
    ).scalar_one_or_none()
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un ingreso con folio {folio!r}",
        )
    return ingreso


def crear_ficha(
    db: Session, data: FichaClinicaCreate, *, salutem_cita_id: int | None = None
) -> FichaClinica:
    """Push: persiste datos clínicos recibidos en el dominio CEPA (D12)."""
    ingreso = _obtener_ingreso_por_folio(db, data.folio)
    ficha = FichaClinica(
        ingreso_id=ingreso.id,
        folio=data.folio,
        origen=data.origen,
        contenido=data.contenido,
        salutem_cita_id=salutem_cita_id,
    )
    db.add(ficha)
    db.flush()
    return ficha


def listar_fichas(db: Session, folio: str) -> list[FichaClinica]:
    """Pull: devuelve todas las fichas clínicas del dominio CEPA para el folio."""
    _obtener_ingreso_por_folio(db, folio)
    return list(
        db.scalars(select(FichaClinica).where(FichaClinica.folio == folio)).all()
    )


def _en_ventana_del_ingreso(fecha, ingreso: Ingreso) -> bool:
    """¿La atención cae dentro del episodio que representa este folio?

    El anclaje es por RUT, así que SALUTEM devuelve TODA la historia de la
    persona, incluidas atenciones de otros ingresos. La ventana del ingreso es
    lo que decide cuáles le pertenecen: desde `fecha_ingreso` y, si el caso ya
    cerró, hasta `fecha_alta`.

    Una atención sin fecha no es atribuible a ningún episodio y se descarta.
    """
    if fecha is None:
        return False
    if fecha < ingreso.fecha_ingreso:
        return False
    return not (ingreso.fecha_alta is not None and fecha > ingreso.fecha_alta)


def _cita_ids_ya_persistidos(db: Session, folio: str) -> set[int]:
    """`salutem_cita_id` de las fichas ya guardadas para este folio.

    Hace idempotente el pull y evita duplicar las fichas que crea el sync. La
    migración 1250 rellenó la columna en las fichas anteriores a ella.
    """
    return set(
        db.scalars(
            select(FichaClinica.salutem_cita_id).where(
                FichaClinica.folio == folio,
                FichaClinica.salutem_cita_id.is_not(None),
            )
        ).all()
    )


def pull_desde_salutem(db: Session, folio: str) -> list[FichaClinica]:
    """Pull desde SALUTEM traduciendo sus fallos a respuestas HTTP con sentido.

    Sin esta traducción cualquier rechazo de SALUTEM llegaba al usuario como un
    500 genérico, indistinguible de un bug del CEPA.
    """
    try:
        return _pull_desde_salutem(db, folio)
    except SalutemRequestError as e:
        if e.codigo == "ERROR_IDENTIFICACION_NO_VALIDA":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "SALUTEM no reconoce el RUT del paciente como válido. "
                    "Revisa el RUT registrado en el ingreso."
                ),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SALUTEM rechazó la consulta ({e.codigo}).",
        ) from e
    except SalutemUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SALUTEM no está respondiendo. Intenta de nuevo en unos minutos.",
        ) from e
    except SalutemError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo consultar SALUTEM ({e.codigo or 'error desconocido'}).",
        ) from e


def _pull_desde_salutem(db: Session, folio: str) -> list[FichaClinica]:
    """Pull desde SALUTEM anclado por RUT (solo lectura, D12).

    SALUTEM no conoce el folio del CEPA. El puente es el RUT del paciente:

        folio → Ingreso.paciente.rut → resolver_persona() → salutem_id
              → listar_atenciones() → obtener_atencion() por cada una

    Se persisten en el dominio CEPA las atenciones que caen dentro de la
    ventana del ingreso y que no estuvieran ya guardadas. Devuelve las fichas
    nuevas; lista vacía si SALUTEM no tiene nada que aportar.
    """
    ingreso = _obtener_ingreso_por_folio(db, folio)
    cliente = get_salutem_client()

    # Solo lectura sobre SALUTEM (D12): ningún método de este flujo escribe.
    persona = cliente.resolver_persona(ingreso.paciente.rut)
    if persona is None:
        return []

    ya_guardados = _cita_ids_ya_persistidos(db, folio)
    nuevas: list[FichaClinica] = []

    for cita in cliente.listar_atenciones(persona.salutem_id):
        if cita.cita_id in ya_guardados:
            continue
        if not _en_ventana_del_ingreso(cita.fecha, ingreso):
            continue
        atencion = cliente.obtener_atencion(persona.salutem_id, cita.cita_id)
        if atencion is None:
            continue
        nuevas.append(
            crear_ficha(
                db,
                FichaClinicaCreate(
                    folio=folio, origen="SALUTEM", contenido=atencion.contenido
                ),
                salutem_cita_id=cita.cita_id,
            )
        )

    return nuevas
