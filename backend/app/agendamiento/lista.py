"""Lista calculada de pacientes por citar de un profesional (lista de trabajo del agendamiento).

Se calcula al vuelo con lo que hay en la BD y la copia de SALUTEM; no se guarda nada. SQL portable a
Postgres y Oracle 19c: los datos por paciente se cargan en lote (sin N+1) con listas IN de a 500.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendamiento import gestion
from app.agendamiento.salutem import _lotes, pacientes_con_hora_vigente, pacientes_sin_vinculo
from app.agendamiento.scheduler import _clave_orden, repartir_carga
from app.agendamiento.schemas import (
    CargaDiaRead,
    PacientePorCitarRead,
    PacientesPorCitarRead,
    UltimaGestionRead,
)
from app.agendamiento.service import _cargar_candidatos, _cargar_disponibilidad
from app.domain.enums import EstadoCaso
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.services.config_alertas import cargar_festivos
from app.services.salutem_sync.incremental import ZONA

# Días hábiles que se oculta a un paciente tras decir "agendada en SALUTEM"; pasado ese plazo, si
# sigue sin hora en SALUTEM, vuelve a la lista con la marca `dijo_agendada_sin_hora`.
DIAS_HABILES_OCULTO_AGENDADA = 3

_PREFIJO_REPOSO = "reposo vigente hasta "


def _inicio_ventana(hoy: date, festivos: frozenset[date]) -> datetime:
    """Inicio (UTC) del día que queda DIAS_HABILES_OCULTO_AGENDADA días hábiles antes de `hoy`.

    Los días hábiles son lunes a viernes sin feriados; el día se toma en hora de Santiago.
    """
    dia = hoy
    restantes = DIAS_HABILES_OCULTO_AGENDADA
    while restantes > 0:
        dia -= timedelta(days=1)
        if dia.weekday() < 5 and dia not in festivos:
            restantes -= 1
    return datetime.combine(dia, time.min, tzinfo=ZONA).astimezone(timezone.utc)


def _a_utc(valor: datetime) -> datetime:
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)


def _nombres(db: Session, paciente_ids: list[int]) -> dict[int, str]:
    nombres: dict[int, str] = {}
    for lote in _lotes(paciente_ids):
        nombres.update({pid: nombre for pid, nombre in db.execute(
            select(Paciente.id, Paciente.nombre).where(Paciente.id.in_(lote))
        )})
    return nombres


def _folios(db: Session, paciente_ids: list[int]) -> dict[int, str]:
    """Folio del ingreso activo con fecha_ingreso más reciente de cada paciente (el id desempata)."""
    mejor: dict[int, tuple[date, int, str]] = {}
    for lote in _lotes(paciente_ids):
        filas = db.execute(
            select(Ingreso.paciente_id, Ingreso.fecha_ingreso, Ingreso.id, Ingreso.folio).where(
                Ingreso.paciente_id.in_(lote), Ingreso.estado == EstadoCaso.ACTIVO.value
            )
        )
        for pid, fecha, ingreso_id, folio in filas:
            if pid not in mejor or (fecha, ingreso_id) > mejor[pid][:2]:
                mejor[pid] = (fecha, ingreso_id, folio)
    return {pid: datos[2] for pid, datos in mejor.items()}


def calcular_pacientes_por_citar(
    db: Session, profesional_id: int, desde: date, hasta: date, hoy: date
) -> PacientesPorCitarRead:
    candidatos = _cargar_candidatos(db, profesional_id, desde, hasta, hoy)

    # 1. Fuera quienes ya tienen hora vigente en SALUTEM.
    con_hora = pacientes_con_hora_vigente(db, [c.paciente_id for c in candidatos], hoy)
    candidatos = [c for c in candidatos if c.paciente_id not in con_hora]

    # 2. Fuera quienes este profesional ya marcó como "agendada en SALUTEM" dentro de la ventana.
    festivos = cargar_festivos(db)
    inicio_ventana = _inicio_ventana(hoy, festivos)
    ids = [c.paciente_id for c in candidatos]
    ocultos = gestion.ocultos_por_agendada(db, profesional_id, ids, inicio_ventana)
    candidatos = [c for c in candidatos if c.paciente_id not in ocultos]
    ids = [c.paciente_id for c in candidatos]

    # 3. Dijeron "agendada" hace más de la ventana y siguen sin hora: vuelven con marca.
    agendadas = gestion.ultima_agendada_por_profesional(db, profesional_id, ids)
    dijo_agendada = {pid for pid, creado in agendadas.items() if _a_utc(creado) < inicio_ventana}

    # 4. Reparto de la carga sobre los días con cupo.
    reparto = repartir_carga(
        candidatos, desde, hasta, _cargar_disponibilidad(db, profesional_id), festivos
    )

    # 5. Filas.
    por_id = {c.paciente_id: c for c in candidatos}
    nombres = _nombres(db, ids)
    folios = _folios(db, ids)
    sin_vinculo = pacientes_sin_vinculo(db, ids)
    gestiones = gestion.ultimas_gestiones(db, ids)

    def fila(pid: int, seccion: str, dia: date | None = None, reposo: date | None = None):
        c = por_id[pid]
        g = gestiones.get(pid)
        return PacientePorCitarRead(
            paciente_id=pid,
            nombre=nombres.get(pid, ""),
            folio=folios.get(pid),
            prioridad=c.prioridad,
            razon=c.razon,
            fecha_objetivo=c.fecha_ctrl,
            dia_sugerido=dia,
            seccion=seccion,
            reposo_hasta=reposo,
            sin_vinculo_salutem=pid in sin_vinculo,
            dijo_agendada_sin_hora=pid in dijo_agendada,
            ultima_gestion=None if g is None else UltimaGestionRead(
                fecha=g.created_at, resultado=g.resultado, usuario=g.usuario, nota=g.nota
            ),
        )

    def clave(pid: int):
        return (*_clave_orden(por_id[pid]), pid)

    asignados = sorted(reparto.asignados, key=lambda r: (r.fecha_candidata, *clave(r.paciente_id)))
    sin_cupo = sorted(reparto.sin_cupo, key=lambda c: clave(c.paciente_id))
    en_reposo = sorted(reparto.en_reposo, key=lambda r: clave(r.paciente_id))

    pacientes = [fila(r.paciente_id, "por_citar", dia=r.fecha_candidata) for r in asignados]
    pacientes += [fila(c.paciente_id, "sin_cupo") for c in sin_cupo]
    pacientes += [
        fila(
            r.paciente_id, "en_reposo",
            reposo=date.fromisoformat((r.excluida_por or "")[len(_PREFIJO_REPOSO):]),
        )
        for r in en_reposo
    ]

    return PacientesPorCitarRead(
        profesional_id=profesional_id,
        desde=desde,
        hasta=hasta,
        por_dia=[CargaDiaRead(fecha=d.fecha, cupo=d.cupo, asignados=d.asignados) for d in reparto.por_dia],
        pacientes=pacientes,
    )
