"""Servicio de agendamiento: disponibilidad de los profesionales y carga de candidatos desde la BD.

El SIGE ya no agenda: las horas se reservan en SALUTEM. Este módulo arma los candidatos de la lista
"Pacientes por citar" (ver lista.py); el reparto de carga (reposo, prioridad, cupo) vive en
scheduler.py. Solo sabe de modelos SQLAlchemy y del patrón de repositorio.

Esquema real que se consulta:
  - control_medico: ingreso_id, proximo_control, medico_tratante. No tiene paciente_id ni
    profesional_id directos; el paciente se obtiene vía ingreso.
  - licencia_medica: ingreso_id, inicio_reposo, fin_reposo. El paciente también sale vía ingreso.
  - receta, ligada a reg_farmacologico.ingreso_id. No tiene requiere_seguimiento ni gestionada;
    una fecha_revision futura hace de seguimiento pendiente.
  - profesional_id en DisponibilidadProf es el id del catálogo `profesional` (migración 1340).

Candidatos por profesional:
  control_medico y reg_farmacologico guardan al médico como texto (medico_tratante), no
  como id. Se cruzan por nombre: profesional.nombre = TRIM(medico_tratante), el mismo
  criterio con que el catálogo se siembra desde SALUTEM.
  - Controles (P1/P2): cuenta el médico del ÚLTIMO control del ingreso, que es quien fijó
    el proximo_control que se está agendando.
  - Recetas (P3): receta no tiene médico; se usa el del registro farmacológico al que
    pertenece (reg_farmacologico.medico_tratante), que es el que la emite y revisa.
  Un profesional_id que no existe en el catálogo no tiene pacientes: lista vacía.
  Solo entran pacientes con ingreso activo. proximo_agendado solo se lee: el SIGE nunca lo
  escribe, lo escribe únicamente el sync de SALUTEM.
  Quién deja la lista: un control de origen CEPA con proximo_agendado = TRUE se excluye aquí; en los
  de origen SALUTEM el flag no manda y el paciente con hora vigente en la copia de SALUTEM
  (agendamiento.salutem.pacientes_con_hora_vigente) lo saca lista.calcular_pacientes_por_citar.
"""

from datetime import date, timedelta

from sqlalchemy import false, func, or_, select, true
from sqlalchemy.orm import Session

from app.agendamiento.enums import PrioridadCita
from app.agendamiento.models import DisponibilidadProf, PropuestaAgenda
from app.agendamiento.salutem import _lotes
from app.agendamiento.scheduler import (
    Candidato,
    DisponibilidadDia,
    ReposoPaciente,
)
from app.audit.service import record_audit
from app.domain.enums import EstadoCaso
from app.services.salutem_sync.controles import ORIGEN as ORIGEN_SALUTEM

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
    """Crea o reemplaza la disponibilidad diaria de un profesional.

    Si ya hay una fila activa para (profesional, día), se actualiza su cupo (UPDATE);
    si no, se crea (CREATE). Así no quedan dos cupos vigentes para el mismo día.
    """
    existente = db.scalars(
        select(DisponibilidadProf)
        .where(DisponibilidadProf.profesional_id == profesional_id,
               DisponibilidadProf.dia_semana == dia_semana,
               DisponibilidadProf.activo == true())
        .order_by(DisponibilidadProf.id)
    ).first()
    if existente is not None:
        cupo_anterior = existente.cupo_diario
        existente.cupo_diario = cupo_diario
        db.flush()
        record_audit(
            db,
            actor=actor,
            action="UPDATE",
            entity="disponibilidad_prof",
            entity_id=str(existente.id),
            valor_anterior=str(cupo_anterior),
            valor_nuevo=str(cupo_diario),
        )
        return existente

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


def dar_de_baja_disponibilidad(
    db: Session,
    disponibilidad_id: int,
    actor: str,
) -> bool:
    """Baja lógica de una disponibilidad activa (activo=False). False si no existe o ya estaba inactiva."""
    dp = db.scalars(
        select(DisponibilidadProf)
        .where(DisponibilidadProf.id == disponibilidad_id,
               DisponibilidadProf.activo == true())
    ).first()
    if dp is None:
        return False
    dp.activo = False
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="DELETE",
        entity="disponibilidad_prof",
        entity_id=str(dp.id),
    )
    return True


def _cargar_disponibilidad(db: Session, profesional_id: int) -> list[DisponibilidadDia]:
    rows = db.scalars(
        select(DisponibilidadProf).where(
            DisponibilidadProf.profesional_id == profesional_id,
            DisponibilidadProf.activo == true(),
        )
        # Con filas duplicadas legadas gana la de menor id, igual que el upsert de crear_disponibilidad.
        .order_by(DisponibilidadProf.id)
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
    from app.models.ingreso import Ingreso
    from app.models.licencia import LicenciaMedica

    if not paciente_ids:
        return {}

    resultado: dict[int, list[ReposoPaciente]] = {pid: [] for pid in paciente_ids}
    # Core ORM — portable Oracle/Postgres (D15): false() renderiza 0/FALSE según dialecto.
    # IN por lotes: Oracle no admite más de 1000 elementos en una lista IN.
    for lote in _lotes(paciente_ids):
        stmt = (
            select(Ingreso.paciente_id, LicenciaMedica.inicio_reposo, LicenciaMedica.fin_reposo)
            .join(Ingreso, Ingreso.id == LicenciaMedica.ingreso_id)
            .where(
                Ingreso.paciente_id.in_(lote),
                LicenciaMedica.anulada == false(),
                LicenciaMedica.inicio_reposo <= fecha_fin,
                LicenciaMedica.fin_reposo >= fecha_ini,
            )
        )
        for pid, inicio, fin in db.execute(stmt):
            resultado[pid].append(ReposoPaciente(inicio=inicio, fin=fin))
    return resultado


def _cargar_candidatos(
    db: Session, profesional_id: int, fecha_ini: date, fecha_fin: date, hoy: date
) -> list[Candidato]:
    """Construye la lista de candidatos a partir de controles y recetas.

    Solo entran pacientes con ingreso activo (EstadoCaso.ACTIVO). Usa control_medico con join a
    ingreso para obtener paciente_id (Desviación 5):
    - Controles vencidos: el control MÁS RECIENTE por ingreso tiene proximo_control < hoy
    - Controles próximos: el control MÁS RECIENTE por ingreso tiene proximo_control entre hoy y
      el fin del rango + 7 días
    - En controles de origen CEPA se excluyen las filas con proximo_agendado = TRUE (ya tienen
      cita programada). En los de origen SALUTEM ese flag no manda: no se filtra aquí y la hora
      vigente se verifica contra la copia de SALUTEM en lista.calcular_pacientes_por_citar, donde
      el paciente con hora vigente sale de la lista. El SIGE nunca escribe SALUTEM.
    - Recetas: hoy ≤ fecha_revision ≤ hoy + VENTANA_SEGUIMIENTO_RECETA_DIAS
               y fecha_envio IS NULL (proxy de receta no gestionada — RN-6)

    Solo se usa el último control_medico por ingreso (subquery MAX fecha_control) para
    evitar que controles históricos dupliquen candidatos.

    Solo entran los pacientes del profesional pedido (ver docstring del módulo): el
    médico del último control para P1/P2 y el del registro farmacológico para P3.
    """
    from app.models.control_medico import ControlMedico
    from app.models.farmacos import Receta, RegistroFarmacologico
    from app.models.ingreso import Ingreso
    from app.models.profesional import Profesional

    nombre_prof = db.scalar(select(Profesional.nombre).where(Profesional.id == profesional_id))
    if nombre_prof is None:
        return []

    vistos: dict[int, Candidato] = {}

    # Subquery portable (sin DISTINCT ON) que retorna solo el último control por ingreso.
    # Se usa MAX(fecha_control) como clave del control más reciente — D15.
    _max_fc_sub = (
        select(
            ControlMedico.ingreso_id,
            func.max(ControlMedico.fecha_control).label("max_fc"),
        )
        .group_by(ControlMedico.ingreso_id)
        .subquery("latest")
    )

    # Alias del control más reciente (auto-join sobre max_fc)
    _cm = ControlMedico
    _latest_ctrl = (
        select(
            _cm.ingreso_id,
            _cm.proximo_control,
            _cm.proximo_agendado,
            _cm.medico_tratante,
            _cm.origen,
        )
        .join(
            _max_fc_sub,
            (_cm.ingreso_id == _max_fc_sub.c.ingreso_id)
            & (_cm.fecha_control == _max_fc_sub.c.max_fc),
        )
        .subquery("lc")
    )

    # 1. Controles vencidos (proximo_control < hoy, último control por ingreso) — Desviación 5
    stmt_vencidos = (
        select(Ingreso.paciente_id, _latest_ctrl.c.proximo_control)
        .join(Ingreso, Ingreso.id == _latest_ctrl.c.ingreso_id)
        .where(
            Ingreso.estado == EstadoCaso.ACTIVO.value,
            _latest_ctrl.c.proximo_control.isnot(None),
            _latest_ctrl.c.proximo_control < hoy,
            # En controles de SALUTEM el flag no manda: la hora se verifica contra la copia.
            or_(_latest_ctrl.c.origen == ORIGEN_SALUTEM, _latest_ctrl.c.proximo_agendado == false()),
            func.trim(_latest_ctrl.c.medico_tratante) == nombre_prof,
        )
    )
    ctrl_vencidos = db.execute(stmt_vencidos).fetchall()

    pid_list: list[int] = []
    vencidos_rows: list[tuple] = list(ctrl_vencidos)
    pid_list.extend(row[0] for row in vencidos_rows)

    # 2. Controles próximos — Desviación 5
    horizonte = fecha_fin + timedelta(days=7)
    stmt_proximos = (
        select(Ingreso.paciente_id, _latest_ctrl.c.proximo_control)
        .join(Ingreso, Ingreso.id == _latest_ctrl.c.ingreso_id)
        .where(
            Ingreso.estado == EstadoCaso.ACTIVO.value,
            _latest_ctrl.c.proximo_control.isnot(None),
            _latest_ctrl.c.proximo_control >= hoy,
            _latest_ctrl.c.proximo_control <= horizonte,
            # En controles de SALUTEM el flag no manda: la hora se verifica contra la copia.
            or_(_latest_ctrl.c.origen == ORIGEN_SALUTEM, _latest_ctrl.c.proximo_agendado == false()),
            func.trim(_latest_ctrl.c.medico_tratante) == nombre_prof,
        )
    )
    ctrl_proximos = db.execute(stmt_proximos).fetchall()

    proximos_rows: list[tuple] = list(ctrl_proximos)
    pid_list.extend(row[0] for row in proximos_rows)

    # 3. Recetas con revisión pendiente dentro de la ventana (RN-6, Desviación 7)
    # Sólo recetas cuya fecha_revision cae en [hoy, hoy+VENTANA] y fecha_envio IS NULL
    # (fecha_envio IS NULL = receta no gestionada/despachada, proxy de RN-6)
    limite_revision = hoy + timedelta(days=VENTANA_SEGUIMIENTO_RECETA_DIAS)
    stmt_recetas = (
        select(Ingreso.paciente_id)
        .distinct()
        .join(RegistroFarmacologico, RegistroFarmacologico.ingreso_id == Ingreso.id)
        .join(Receta, Receta.registro_id == RegistroFarmacologico.id)
        .where(
            Ingreso.estado == EstadoCaso.ACTIVO.value,
            Receta.fecha_revision >= hoy,
            Receta.fecha_revision <= limite_revision,
            Receta.fecha_envio.is_(None),  # RN-6: excluir recetas ya gestionadas
            func.trim(RegistroFarmacologico.medico_tratante) == nombre_prof,
        )
    )
    recetas = db.execute(stmt_recetas).fetchall()

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


# ─── Consulta ──────────────────────────────────────────────────────────────────

def obtener_propuesta(db: Session, propuesta_id: int) -> PropuestaAgenda | None:
    return db.get(PropuestaAgenda, propuesta_id)
