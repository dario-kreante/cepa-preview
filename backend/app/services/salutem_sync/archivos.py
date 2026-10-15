"""Copia de la biblioteca de archivos de SALUTEM (solo metadata).

En cada ciclo `caliente` se lista la biblioteca de las personas con un control de los
últimos DIAS_RECIENTES días: el médico suele subir la licencia o la receta al final del
día o días después, así que no basta con listarla al crear el control. Lo que deja de
aparecer queda con `desaparecido_en`; nunca se borra una fila.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.errors import SalutemAuthError, SalutemError, SalutemUnavailableError
from app.integrations.salutem.models import ArchivoSalutem
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.control_medico import ControlMedico
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion
from app.services.salutem_sync.barrido import describir_error
from app.services.salutem_sync.incremental import hoy_en_santiago
from app.services.salutem_sync.ritmo import Ritmo

DIAS_RECIENTES = 7
log = logging.getLogger("salutem_sync")


@dataclass
class ResultadoArchivos:
    personas: int = 0
    errores: list[str] = field(default_factory=list)


def _personas_con_control_reciente(db: Session, ahora: datetime) -> list[int]:
    desde = hoy_en_santiago(ahora) - timedelta(days=DIAS_RECIENTES)
    return list(
        db.scalars(
            select(SalutemAtencion.persona_id)
            .join(ControlMedico, ControlMedico.salutem_cita_id == SalutemAtencion.cita_id)
            .where(ControlMedico.fecha_control >= desde)
            .distinct()
            .order_by(SalutemAtencion.persona_id)
        )
    )


def guardar_archivos(db: Session, persona_id: int, archivos: list[ArchivoSalutem], ahora: datetime) -> None:
    vistos = {a.archivo_id for a in archivos}
    for a in archivos:
        fila = db.get(SalutemArchivo, a.archivo_id)
        if fila is None:
            fila = SalutemArchivo(archivo_id=a.archivo_id, persona_id=persona_id)
            db.add(fila)
        fila.nombre, fila.tipo, fila.fecha_creacion = a.nombre, a.tipo, a.fecha_creacion
        fila.visto_ultima_vez, fila.desaparecido_en = ahora, None
    for fila in db.scalars(
        select(SalutemArchivo).where(
            SalutemArchivo.persona_id == persona_id, SalutemArchivo.desaparecido_en.is_(None)
        )
    ):
        if fila.archivo_id not in vistos:
            fila.desaparecido_en = ahora
    db.flush()


def refrescar_archivos(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    ahora: datetime,
    al_avanzar: Callable[[], None] | None = None,
) -> ResultadoArchivos:
    """Lista la biblioteca de cada persona con control reciente y guarda su metadata.

    Una persona que falla se registra y se salta, sin afectar a las demás: la vinculación
    de este ciclo ya está hecha y no se pierde. Una credencial rechazada aborta, como en el
    resto del sync. Si SALUTEM no responde (tras los reintentos del ritmo) se corta el
    bucle con un solo error: insistir persona por persona solo alargaría el ciclo.
    `al_avanzar` se llama tras cada persona (el orquestador renueva el lease).
    """
    r = ResultadoArchivos()
    for persona_id in _personas_con_control_reciente(db, ahora):
        try:
            archivos = ritmo.llamar(cliente.listar_archivos, persona_id)
            with db.begin_nested():
                guardar_archivos(db, persona_id, archivos, ahora)
            r.personas += 1
        except SalutemAuthError:
            raise
        except SalutemUnavailableError:
            r.errores.append("SALUTEM no responde; biblioteca pospuesta al próximo ciclo")
            break
        except SalutemError as e:
            r.errores.append(f"archivos de la persona {persona_id}: {describir_error(e)}")
        except Exception as e:  # noqa: BLE001 — una persona mala no debe frenar a las demás
            log.warning("Biblioteca de la persona %s falló: %s: %s", persona_id, type(e).__name__, e)
            r.errores.append(f"archivos de la persona {persona_id}: {type(e).__name__}: {e}")
        if al_avanzar is not None:
            al_avanzar()
    return r
