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

Limitación conocida — pool único de candidatos:
  Los candidatos son clínica-wide (no hay filtro por profesional en control_medico, ya que
  esa tabla carece de profesional_id). El mapeo por-profesional vía medico_tratante está
  planificado antes del despliegue multi-profesional.
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

def _cargar_reposos_batch(
    db: Session,
    paciente_ids: list[int],
    fecha_ini: date,
    fecha_fin: date,
) -> dict[int, list[ReposoPaciente]]:
    """Carga en UNA sola query los reposos de todos los pacientes del conjunto candidato.

    Adaptación Desviación 6: usa licencia_medica con join a ingreso para obtener paciente_id.
    Campos reales: inicio_reposo, fin_reposo (no reposo_inicio/reposo_fin del plan).

    Evita el N+1 de _cargar_reposos por paciente (~800 round-trips al volumen objetivo).
    Retorna un dict {paciente_id: [ReposoPaciente, ...]}.
    """
    from sqlalchemy import text

    if not paciente_ids:
        return {}

    rows = db.execute(text(
        "SELECT i.paciente_id, lm.inicio_reposo, lm.fin_reposo "
        "FROM licencia_medica lm "
        "JOIN ingreso i ON i.id = lm.ingreso_id "
        "WHERE i.paciente_id = ANY(:pids) "
        "  AND lm.anulada = FALSE "
        "  AND lm.inicio_reposo <= :fin "
        "  AND lm.fin_reposo >= :ini"
    ), {"pids": paciente_ids, "ini": fecha_ini, "fin": fecha_fin}).fetchall()

    resultado: dict[int, list[ReposoPaciente]] = {pid: [] for pid in paciente_ids}
    for r in rows:
        resultado[r[0]].append(ReposoPaciente(inicio=r[1], fin=r[2]))
    return resultado


def _cargar_candidatos(
    db: Session, profesional_id: int, fecha_ini: date, fecha_fin: date
) -> list[Candidato]:
    """Construye la lista de candidatos a partir de controles y recetas.

    Adaptación Desviación 5: usa control_medico con join a ingreso para obtener paciente_id.
    - Controles vencidos: el control MÁS RECIENTE por ingreso tiene proximo_control < hoy
    - Controles próximos: el control MÁS RECIENTE por ingreso tiene proximo_control en ventana
    - Se excluyen filas con proximo_agendado = TRUE (ya tienen cita programada)
    - Recetas: hoy ≤ fecha_revision ≤ hoy + VENTANA_SEGUIMIENTO_RECETA_DIAS
               y fecha_envio IS NULL (proxy de receta no gestionada — RN-6)

    Solo se usa el último control_medico por ingreso (subquery MAX fecha_control) para
    evitar que controles históricos desencadenen propuestas duplicadas.

    profesional_id no se usa como filtro en control_medico (no existe ese campo entero
    en la tabla real). La selección por profesional se hace via DisponibilidadProf.
    """
    from sqlalchemy import text
    hoy = date.today()

    vistos: dict[int, Candidato] = {}

    # Subquery portable (sin DISTINCT ON) que retorna solo el último control por ingreso.
    # Se usa MAX(fecha_control) como clave del control más reciente.
    _latest_ctrl = (
        "SELECT cm.ingreso_id, cm.proximo_control, cm.proximo_agendado "
        "FROM control_medico cm "
        "INNER JOIN ("
        "  SELECT ingreso_id, MAX(fecha_control) AS max_fc "
        "  FROM control_medico "
        "  GROUP BY ingreso_id"
        ") latest ON latest.ingreso_id = cm.ingreso_id "
        "         AND latest.max_fc = cm.fecha_control"
    )

    # 1. Controles vencidos (proximo_control < hoy, último control por ingreso) — Desviación 5
    ctrl_vencidos = db.execute(text(
        f"SELECT i.paciente_id, lc.proximo_control "
        f"FROM ({_latest_ctrl}) lc "
        f"JOIN ingreso i ON i.id = lc.ingreso_id "
        f"WHERE lc.proximo_control IS NOT NULL "
        f"  AND lc.proximo_control < :hoy "
        f"  AND lc.proximo_agendado = FALSE"
    ), {"hoy": hoy}).fetchall()

    pid_list: list[int] = []
    vencidos_rows: list[tuple] = list(ctrl_vencidos)
    pid_list.extend(row[0] for row in vencidos_rows)

    # 2. Controles próximos — Desviación 5
    horizonte = fecha_fin + timedelta(days=7)
    ctrl_proximos = db.execute(text(
        f"SELECT i.paciente_id, lc.proximo_control "
        f"FROM ({_latest_ctrl}) lc "
        f"JOIN ingreso i ON i.id = lc.ingreso_id "
        f"WHERE lc.proximo_control IS NOT NULL "
        f"  AND lc.proximo_control >= :hoy "
        f"  AND lc.proximo_control <= :horizonte "
        f"  AND lc.proximo_agendado = FALSE"
    ), {"hoy": hoy, "horizonte": horizonte}).fetchall()

    proximos_rows: list[tuple] = list(ctrl_proximos)
    pid_list.extend(row[0] for row in proximos_rows)

    # 3. Recetas con revisión pendiente dentro de la ventana (RN-6, Desviación 7)
    # Sólo recetas cuya fecha_revision cae en [hoy, hoy+VENTANA] y fecha_envio IS NULL
    # (fecha_envio IS NULL = receta no gestionada/despachada, proxy de RN-6)
    limite_revision = hoy + timedelta(days=VENTANA_SEGUIMIENTO_RECETA_DIAS)
    recetas = db.execute(text(
        "SELECT DISTINCT i.paciente_id "
        "FROM receta r "
        "JOIN reg_farmacologico rf ON rf.id = r.registro_id "
        "JOIN ingreso i ON i.id = rf.ingreso_id "
        "WHERE r.fecha_revision >= :hoy "
        "  AND r.fecha_revision <= :limite "
        "  AND r.fecha_envio IS NULL"  # RN-6: excluir recetas ya gestionadas
    ), {"hoy": hoy, "limite": limite_revision}).fetchall()

    recetas_rows: list[tuple] = list(recetas)
    pid_list.extend(row[0] for row in recetas_rows)

    # Batch-load de todos los reposos en una sola query (Fix 5: evita N+1)
    unique_pids = list({pid for pid in pid_list})
    reposos_map = _cargar_reposos_batch(db, unique_pids, fecha_ini, fecha_fin)

    # Construir candidatos a partir de los datos ya cargados
    for pid, fecha_ctrl in vencidos_rows:
        reposos = reposos_map.get(pid, [])
        vistos[pid] = Candidato(
            paciente_id=pid,
            prioridad=PrioridadCita.CONTROL_VENCIDO,
            razon=f"control vencido desde {fecha_ctrl}",
            fecha_ctrl=fecha_ctrl,
            reposos=reposos,
        )

    for pid, fecha_ctrl in proximos_rows:
        if pid not in vistos:
            reposos = reposos_map.get(pid, [])
            vistos[pid] = Candidato(
                paciente_id=pid,
                prioridad=PrioridadCita.CONTROL_PROXIMO,
                razon=f"control próximo el {fecha_ctrl}",
                fecha_ctrl=fecha_ctrl,
                reposos=reposos,
            )

    for (pid,) in recetas_rows:
        if pid not in vistos:
            reposos = reposos_map.get(pid, [])
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
        # RN-1: excluida_por != None significa que la cita fue descartada (ej. reposo vigente)
        # — aunque su estado sea 'propuesta', no debe ser confirmable.
        if cita.estado == EstadoCita.PROPUESTA.value and cita.excluida_por is None:
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
