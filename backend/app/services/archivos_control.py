"""Documentos de la biblioteca de SALUTEM que acompañan a un control.

La API de SALUTEM no une el archivo con la cita ni dice si es licencia o receta: se
unen por fecha. Un control lleva los archivos de la persona creados desde el día del
control hasta el día anterior al control siguiente del ingreso, con un tope de
VENTANA_DIAS. No se clasifican: la encargada los abre y decide.
"""

from datetime import datetime, time, timedelta

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
    fin = control.fecha_control + timedelta(days=VENTANA_DIAS)
    siguiente = db.scalar(
        select(func.min(ControlMedico.fecha_control)).where(
            ControlMedico.ingreso_id == control.ingreso_id,
            ControlMedico.fecha_control > control.fecha_control,
        )
    )
    if siguiente is not None and siguiente < fin:
        fin = siguiente
    return list(
        db.scalars(
            select(SalutemArchivo)
            .where(
                SalutemArchivo.persona_id == persona_id,
                SalutemArchivo.desaparecido_en.is_(None),
                SalutemArchivo.fecha_creacion >= datetime.combine(control.fecha_control, time.min),
                SalutemArchivo.fecha_creacion < datetime.combine(fin, time.min),
            )
            .order_by(SalutemArchivo.fecha_creacion, SalutemArchivo.archivo_id)
        )
    )
