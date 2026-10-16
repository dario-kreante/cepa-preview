"""A qué paciente, ingreso y atención de SALUTEM corresponde una alerta.

El panel lo usa para gestionar la alerta en el lugar: registrar la licencia del control
o de la atención, o ir a los fármacos del paciente. Las alertas de un control llegan por
su ingreso; las de una atención médica que no es control (caso_tipo salutem_atencion),
por la persona de SALUTEM y el ingreso cuya ventana contiene la fecha de la atención.
"""

from datetime import date

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alertas import AlertaNotif
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.services.ficha_clinica import _en_ventana_del_ingreso
from app.services.salutem_sync.filtro import cruce_con_paciente


class AlertaContextoRead(BaseModel):
    paciente_id: int | None = None
    paciente_nombre: str | None = None
    ingreso_id: int | None = None
    folio: str | None = None
    # Cita de SALUTEM de la que viene la alerta (control o atención), si la hay.
    cita_id: int | None = None
    fecha: date | None = None


def contexto_de_alerta(db: Session, alerta: AlertaNotif) -> AlertaContextoRead:
    if alerta.caso_id is None:
        return AlertaContextoRead()
    if alerta.caso_tipo == "control_medico":
        control = db.get(ControlMedico, alerta.caso_id)
        if control is None:
            return AlertaContextoRead()
        return _con_ingreso(db.get(Ingreso, control.ingreso_id), control.salutem_cita_id, control.fecha_control)
    if alerta.caso_tipo == "salutem_atencion":
        atencion = db.get(SalutemAtencion, alerta.caso_id)
        if atencion is None:
            return AlertaContextoRead(cita_id=alerta.caso_id)
        return _con_ingreso(_ingreso_de_atencion(db, atencion), atencion.cita_id, atencion.fecha_cita)
    if alerta.caso_tipo == "paciente":
        paciente = db.get(Paciente, alerta.caso_id)
        if paciente is None:
            return AlertaContextoRead()
        return AlertaContextoRead(paciente_id=paciente.id, paciente_nombre=paciente.nombre)
    if alerta.caso_tipo == "ingreso":
        return _con_ingreso(db.get(Ingreso, alerta.caso_id), None, None)
    return AlertaContextoRead()


def _con_ingreso(ingreso: Ingreso | None, cita_id: int | None, fecha: date | None) -> AlertaContextoRead:
    if ingreso is None:
        return AlertaContextoRead(cita_id=cita_id, fecha=fecha)
    return AlertaContextoRead(
        paciente_id=ingreso.paciente_id,
        paciente_nombre=ingreso.paciente.nombre,
        ingreso_id=ingreso.id,
        folio=ingreso.folio,
        cita_id=cita_id,
        fecha=fecha,
    )


def _ingreso_de_atencion(db: Session, atencion: SalutemAtencion) -> Ingreso | None:
    paciente_ids = db.scalars(
        select(Paciente.id)
        .join(SalutemPersona, cruce_con_paciente())
        .where(SalutemPersona.salutem_id == atencion.persona_id)
    ).all()
    if not paciente_ids:
        return None
    ingresos = db.scalars(
        select(Ingreso).where(Ingreso.paciente_id.in_(paciente_ids)).order_by(Ingreso.fecha_ingreso.desc())
    ).all()
    return next((i for i in ingresos if _en_ventana_del_ingreso(atencion.fecha_cita, i)), None)
