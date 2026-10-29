"""Documentos de la biblioteca de SALUTEM que acompañan a un control.

La API de SALUTEM no une el archivo con la cita ni dice si es licencia o receta: se
unen por fecha. Un control lleva los archivos de la persona creados desde el día del
control hasta el día anterior al control siguiente del ingreso, con un tope de
VENTANA_DIAS. No se clasifican: la encargada los abre y decide.

`documentos_de_paciente` lista la biblioteca completa del paciente, con la relación
deducida con licencia o receta (ver más abajo), para los módulos Licencias y Fármacos.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.salutem.senales import certificado_reposo, tiene_receta
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion, SalutemPersona
from app.services.salutem_sync.controles import licencia_de_atencion
from app.services.salutem_sync.filtro import cruce_con_paciente

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


# ── Biblioteca completa del paciente (QA-001, 22-10) ─────────────────────────
#
# SALUTEM no dice en qué carpeta está cada archivo (licencias médicas, recetas médicas…):
# el listado trae solo id, nombre, fecha, tipo ("documento"/"imagen") y descripción. Lo
# único confiable y unido a la cita es el formulario de la atención. Por eso la relación
# con licencia o receta se DEDUCE: un archivo se relaciona con la última atención de la
# persona que indicó licencia o receta, si se subió ese día o dentro de VENTANA_DIAS. Es
# una orientación para la encargada, no la carpeta de SALUTEM.

RELACIONES = ("licencia", "receta")


@dataclass(frozen=True)
class DocumentoPaciente:
    archivo_id: int
    persona_id: int
    nombre: str
    tipo: str | None
    fecha_creacion: datetime | None
    licencia: bool
    receta: bool
    # Fecha de la atención de la que se dedujo la relación (None si no hay).
    fecha_atencion: date | None


def personas_de_paciente(db: Session, paciente_id: int) -> set[int]:
    """Las personas de SALUTEM del paciente: por RUT o id (como la vinculación) y por las
    atenciones ya unidas a sus controles."""
    por_cruce = db.scalars(
        select(SalutemPersona.salutem_id)
        .join(Paciente, cruce_con_paciente())
        .where(Paciente.id == paciente_id)
    )
    por_controles = db.scalars(
        select(SalutemAtencion.persona_id)
        .join(ControlMedico, ControlMedico.salutem_cita_id == SalutemAtencion.cita_id)
        .join(Ingreso, Ingreso.id == ControlMedico.ingreso_id)
        .where(Ingreso.paciente_id == paciente_id)
    )
    return {*por_cruce, *por_controles}


def _senales_por_dia(db: Session, personas: set[int]) -> dict[int, dict[date, tuple[bool, bool]]]:
    """Por persona y día: (licencia, receta) indicadas en sus atenciones de ese día."""
    senales: dict[int, dict[date, tuple[bool, bool]]] = {}
    for atencion, licencia_control in db.execute(
        select(SalutemAtencion, ControlMedico.tiene_licencia)
        .outerjoin(ControlMedico, ControlMedico.salutem_cita_id == SalutemAtencion.cita_id)
        .where(
            SalutemAtencion.persona_id.in_(personas),
            SalutemAtencion.desaparecida_en.is_(None),
            SalutemAtencion.fecha_cita.is_not(None),
        )
    ):
        c = atencion.contenido or {}
        licencia = (
            bool(licencia_control)
            or certificado_reposo(c)
            or licencia_de_atencion(c, atencion.fecha_cita) is not None
        )
        receta = tiene_receta(c)
        if not (licencia or receta):
            continue
        dias = senales.setdefault(atencion.persona_id, {})
        previa = dias.get(atencion.fecha_cita, (False, False))
        dias[atencion.fecha_cita] = (previa[0] or licencia, previa[1] or receta)
    return senales


def _relacion(
    senales: dict[date, tuple[bool, bool]], creado: datetime | None
) -> tuple[bool, bool, date | None]:
    if creado is None:
        return False, False, None
    dia = creado.date()
    candidatas = [f for f in senales if f <= dia < f + timedelta(days=VENTANA_DIAS)]
    if not candidatas:
        return False, False, None
    origen = max(candidatas)
    licencia, receta = senales[origen]
    return licencia, receta, origen


def documentos_de_paciente(
    db: Session, paciente_id: int, relacion: str | None = None
) -> list[DocumentoPaciente]:
    """La biblioteca de SALUTEM del paciente, del más nuevo al más antiguo.

    `relacion` ("licencia" o "receta") deja solo los relacionados con esa indicación.
    """
    personas = personas_de_paciente(db, paciente_id)
    if not personas:
        return []
    senales = _senales_por_dia(db, personas)
    documentos = []
    for a in db.scalars(
        select(SalutemArchivo)
        .where(SalutemArchivo.persona_id.in_(personas), SalutemArchivo.desaparecido_en.is_(None))
        .order_by(SalutemArchivo.fecha_creacion.desc().nulls_last(), SalutemArchivo.archivo_id.desc())
    ):
        licencia, receta, origen = _relacion(senales.get(a.persona_id, {}), a.fecha_creacion)
        if (relacion == "licencia" and not licencia) or (relacion == "receta" and not receta):
            continue
        documentos.append(
            DocumentoPaciente(
                archivo_id=a.archivo_id, persona_id=a.persona_id, nombre=a.nombre, tipo=a.tipo,
                fecha_creacion=a.fecha_creacion, licencia=licencia, receta=receta,
                fecha_atencion=origen,
            )
        )
    return documentos
