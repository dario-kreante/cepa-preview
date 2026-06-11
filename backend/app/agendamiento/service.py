"""Servicio de agendamiento: orquesta la carga de BD y llama al scheduler puro.

La lógica algorítmica (exclusión por reposo, priorización, cupo) vive en scheduler.py.
Este módulo solo sabe de modelos SQLAlchemy y del patrón de repositorio.

Adaptaciones respecto al plan (Deviaciones 5-7):
  - Tabla real: control_medico (no control). Columnas: ingreso_id, proximo_control,
    medico_tratante. Sin paciente_id/profesional_id directos — se obtiene vía ingreso.
  - Tabla real: licencia_medica (no licencia). Columnas: ingreso_id, inicio_reposo,
    fin_reposo. Sin paciente_id directo — se obtiene vía ingreso.
  - Tabla real: receta, ligada a reg_farmacologico.ingreso_id. Sin requiere_seguimiento
    ni gestionada; se usa fecha_revision futura como proxy de seguimiento pendiente.
  - profesional_id en DisponibilidadProf es un ID interno del módulo de agendamiento.
    Las queries a control_medico retornan todos los controles próximos sin filtrar por
    profesional_id (ya que control_medico no tiene ese campo entero).
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendamiento.enums import EstadoCita, EstadoPropuesta, PrioridadCita
from app.agendamiento.models import CitaPropuesta, DisponibilidadProf, PropuestaAgenda
from app.agendamiento.scheduler import (
    Candidato,
    DisponibilidadDia,
    ReposoPaciente,
    proponer_agenda,
    proponer_agenda_semana,
)
from app.agendamiento.schemas import GenerarPropuestaRequest
from app.audit.service import record_audit

# ─── Ventana de seguimiento de receta (parametrizable — RN-6) ──────────────────
VENTANA_SEGUIMIENTO_RECETA_DIAS: int = 30


# ─── Disponibilidad ────────────────────────────────────────────────────────────

def crear_disponibilidad(
    db: Session,
    profesional_id: int,
    dia_semana: int,
    cupo_diario: int,
    actor: str,
) -> DisponibilidadProf:
    """Crea o reemplaza la disponibilidad diaria de un profesional."""
    dp = DisponibilidadProf(
        profesional_id=profesional_id,
        dia_semana=dia_semana,
        cupo_diario=cupo_diario,
        activo=True,
    )
    db.add(dp)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="CREATE",
        entity="disponibilidad_prof",
        entity_id=str(dp.id),
    )
    return dp


def _cargar_disponibilidad(db: Session, profesional_id: int) -> list[DisponibilidadDia]:
    rows = db.scalars(
        select(DisponibilidadProf).where(
            DisponibilidadProf.profesional_id == profesional_id,
            DisponibilidadProf.activo.is_(True),
        )
    ).all()
    return [DisponibilidadDia(dia_semana=r.dia_semana, cupo=r.cupo_diario) for r in rows]


# ─── Carga de candidatos desde BD ───────────────────────────────────────────────

def _cargar_reposos(
    db: Session, paciente_id: int, fecha_ini: date, fecha_fin: date
) -> list[ReposoPaciente]:
    """Carga los reposos del paciente que se solapan con el rango de fechas.

    Adaptación Desviación 6: usa licencia_medica con join a ingreso para obtener paciente_id.
    Campos reales: inicio_reposo, fin_reposo (no reposo_inicio/reposo_fin del plan).
    """
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT lm.inicio_reposo, lm.fin_reposo "
        "FROM licencia_medica lm "
        "JOIN ingreso i ON i.id = lm.ingreso_id "
        "WHERE i.paciente_id = :pid "
        "  AND lm.anulada = FALSE "
        "  AND lm.inicio_reposo <= :fin "
        "  AND lm.fin_reposo >= :ini"
    ), {"pid": paciente_id, "ini": fecha_ini, "fin": fecha_fin}).fetchall()
    return [ReposoPaciente(inicio=r[0], fin=r[1]) for r in rows]


def _cargar_candidatos(
    db: Session, profesional_id: int, fecha_ini: date, fecha_fin: date
) -> list[Candidato]:
    """Construye la lista de candidatos a partir de controles y recetas.

    Adaptación Desviación 5: usa control_medico con join a ingreso para obtener paciente_id.
    - Controles vencidos: proximo_control < hoy (campo real: proximo_control)
    - Controles próximos: hoy ≤ proximo_control ≤ fecha_fin + 7 días
    - Recetas: fecha_revision >= hoy (revisión futura = seguimiento pendiente, Desviación 7)

    profesional_id no se usa como filtro en control_medico (no existe ese campo entero
    en la tabla real). La selección por profesional se hace via DisponibilidadProf.
    """
    from sqlalchemy import text
    hoy = date.today()

    vistos: dict[int, Candidato] = {}

    # 1. Controles vencidos (proximo_control < hoy) — Desviación 5
    ctrl_vencidos = db.execute(text(
        "SELECT i.paciente_id, cm.proximo_control "
        "FROM control_medico cm "
        "JOIN ingreso i ON i.id = cm.ingreso_id "
        "WHERE cm.proximo_control IS NOT NULL "
        "  AND cm.proximo_control < :hoy"
    ), {"hoy": hoy}).fetchall()

    for row in ctrl_vencidos:
        pid, fecha_ctrl = row[0], row[1]
        reposos = _cargar_reposos(db, pid, fecha_ini, fecha_fin)
        vistos[pid] = Candidato(
            paciente_id=pid,
            prioridad=PrioridadCita.CONTROL_VENCIDO,
            razon=f"control vencido desde {fecha_ctrl}",
            fecha_ctrl=fecha_ctrl,
            reposos=reposos,
        )

    # 2. Controles próximos — Desviación 5
    horizonte = fecha_fin + timedelta(days=7)
    ctrl_proximos = db.execute(text(
        "SELECT i.paciente_id, cm.proximo_control "
        "FROM control_medico cm "
        "JOIN ingreso i ON i.id = cm.ingreso_id "
        "WHERE cm.proximo_control IS NOT NULL "
        "  AND cm.proximo_control >= :hoy "
        "  AND cm.proximo_control <= :horizonte"
    ), {"hoy": hoy, "horizonte": horizonte}).fetchall()

    for row in ctrl_proximos:
        pid, fecha_ctrl = row[0], row[1]
        if pid not in vistos:
            reposos = _cargar_reposos(db, pid, fecha_ini, fecha_fin)
            vistos[pid] = Candidato(
                paciente_id=pid,
                prioridad=PrioridadCita.CONTROL_PROXIMO,
                razon=f"control próximo el {fecha_ctrl}",
                fecha_ctrl=fecha_ctrl,
                reposos=reposos,
            )

    # 3. Recetas con revisión futura pendiente (RN-6, Desviación 7)
    # La tabla receta no tiene requiere_seguimiento/gestionada; se usa fecha_revision futura
    limite_emision = hoy - timedelta(days=VENTANA_SEGUIMIENTO_RECETA_DIAS)
    recetas = db.execute(text(
        "SELECT DISTINCT i.paciente_id "
        "FROM receta r "
        "JOIN reg_farmacologico rf ON rf.id = r.registro_id "
        "JOIN ingreso i ON i.id = rf.ingreso_id "
        "WHERE r.fecha_revision >= :hoy "
        "  AND r.fecha_emision >= :limite"
    ), {"hoy": hoy, "limite": limite_emision}).fetchall()

    for row in recetas:
        pid = row[0]
        if pid not in vistos:
            reposos = _cargar_reposos(db, pid, fecha_ini, fecha_fin)
            vistos[pid] = Candidato(
                paciente_id=pid,
                prioridad=PrioridadCita.SEGUIMIENTO_RECETA,
                razon="seguimiento de receta",
                fecha_ctrl=None,
                reposos=reposos,
            )

    return list(vistos.values())


# ─── Generación de propuesta ────────────────────────────────────────────────────

def generar_propuesta(
    db: Session,
    req: GenerarPropuestaRequest,
    actor: str,
) -> PropuestaAgenda:
    """Genera y persiste una PropuestaAgenda con sus CitaPropuesta.

    Registra auditoría (RN-9). No hace commit — el caller (router) es responsable.
    """
    disponibilidad = _cargar_disponibilidad(db, req.profesional_id)
    candidatos = _cargar_candidatos(db, req.profesional_id, req.fecha_inicio, req.fecha_fin)

    propuesta = PropuestaAgenda(
        profesional_id=req.profesional_id,
        tipo=req.tipo.value,
        fecha_inicio=req.fecha_inicio,
        fecha_fin=req.fecha_fin,
        estado=EstadoPropuesta.BORRADOR.value,
        generado_por=actor,
    )
    db.add(propuesta)
    db.flush()

    if req.tipo.value == "diaria":
        resultados = proponer_agenda(
            candidatos=candidatos,
            fecha=req.fecha_inicio,
            disponibilidad=disponibilidad,
        )
    else:
        resultados = proponer_agenda_semana(
            candidatos=candidatos,
            semana_inicio=req.fecha_inicio,
            semana_fin=req.fecha_fin,
            disponibilidad=disponibilidad,
        )

    for r in resultados:
        cita = CitaPropuesta(
            propuesta_id=propuesta.id,
            paciente_id=r.paciente_id,
            fecha_candidata=r.fecha_candidata,
            prioridad=r.prioridad.value,
            razon=r.razon,
            estado=EstadoCita.PROPUESTA.value,
            excluida_por=r.excluida_por,
        )
        db.add(cita)

    record_audit(
        db,
        actor=actor,
        action="CREATE",
        entity="propuesta_agenda",
        entity_id=str(propuesta.id),
    )
    db.flush()
    return propuesta


# ─── Consulta ──────────────────────────────────────────────────────────────────

def obtener_propuesta(db: Session, propuesta_id: int) -> PropuestaAgenda | None:
    return db.get(PropuestaAgenda, propuesta_id)


# ─── Confirmación de citas (CA-7, RN-8, RN-9) ─────────────────────────────────

def confirmar_citas(
    db: Session,
    propuesta_id: int,
    cita_ids: list[int],
    actor: str,
) -> list[CitaPropuesta]:
    """Confirma las citas indicadas y actualiza el estado de la propuesta.

    Las citas confirmadas cuentan como 'citas agendadas' en el denominador de adherencia
    (RN-8). El cambio de estado se graba en auditoría (RN-9).
    """
    propuesta = db.get(PropuestaAgenda, propuesta_id)
    if propuesta is None:
        return []

    confirmadas: list[CitaPropuesta] = []
    for cita_id in cita_ids:
        cita = db.get(CitaPropuesta, cita_id)
        if cita is None or cita.propuesta_id != propuesta_id:
            continue
        if cita.estado == EstadoCita.PROPUESTA.value:
            cita.estado = EstadoCita.CONFIRMADA.value
            confirmadas.append(cita)

    if confirmadas:
        propuesta.estado = EstadoPropuesta.CONFIRMADA.value
        record_audit(
            db,
            actor=actor,
            action="UPDATE",
            entity="propuesta_agenda",
            entity_id=str(propuesta_id),
        )

    db.flush()
    return confirmadas
