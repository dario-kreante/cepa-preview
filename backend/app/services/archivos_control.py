"""Documentos de la biblioteca de SALUTEM que acompañan a un control.

La API de SALUTEM no une el archivo con la cita ni dice si es licencia o receta: se
unen por fecha. Un control lleva los archivos de la persona creados desde el día del
control hasta el día anterior al control siguiente del ingreso, con un tope de
VENTANA_DIAS. No se clasifican: la encargada los abre y decide.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.control_medico import ControlMedico
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion

VENTANA_DIAS = 7


def persona_de_control(db: Session, control: ControlMedico) -> int | None:
    if control.salutem_cita_id is None:
        return None
    atencion = db.get(SalutemAtencion, control.salutem_cita_id)
    return atencion.persona_id if atencion else None


def archivos_de_control(db: Session, control: ControlMedico) -> list[SalutemArchivo]:
    persona_id = persona_de_control(db, control)
    if persona_id is None:
        return []
    siguiente = db.scalar(
        select(func.min(ControlMedico.fecha_control)).where(
            ControlMedico.ingreso_id == control.ingreso_id,
            ControlMedico.fecha_control > control.fecha_control,
        )
    )
    return _archivos(db, persona_id, control.fecha_control, siguiente)


def archivos_de_atencion(db: Session, atencion: SalutemAtencion) -> list[SalutemArchivo]:
    """Documentos de una atención que no es control: hasta la atención siguiente de la persona."""
    if atencion.fecha_cita is None:
        return []
    siguiente = db.scalar(
        select(func.min(SalutemAtencion.fecha_cita)).where(
            SalutemAtencion.persona_id == atencion.persona_id,
            SalutemAtencion.fecha_cita > atencion.fecha_cita,
            SalutemAtencion.desaparecida_en.is_(None),
        )
    )
    return _archivos(db, atencion.persona_id, atencion.fecha_cita, siguiente)


def _archivos(db: Session, persona_id: int, desde: date, siguiente: date | None) -> list[SalutemArchivo]:
    fin = desde + timedelta(days=VENTANA_DIAS)
    if siguiente is not None and siguiente < fin:
        fin = siguiente
    return list(
        db.scalars(
            select(SalutemArchivo)
            .where(
                SalutemArchivo.persona_id == persona_id,
                SalutemArchivo.desaparecido_en.is_(None),
                SalutemArchivo.fecha_creacion >= datetime.combine(desde, time.min),
                SalutemArchivo.fecha_creacion < datetime.combine(fin, time.min),
            )
            .order_by(SalutemArchivo.fecha_creacion, SalutemArchivo.archivo_id)
        )
    )
