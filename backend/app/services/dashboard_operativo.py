"""Dashboard operativo — indicadores con los datos que el SIGE tiene hoy.

La tabla local ``cita`` no la llena ningún proceso: las atenciones reales viven en
la copia de SALUTEM (``salutem_cita``). Este servicio arma el resumen desde ahí y
desde los módulos que sí se usan (ingresos, licencias, ODAs, controles, alertas,
borradores de SALUTEM).

Especialidad y profesional de la cita vienen en el JSON crudo (``contenido``), que
no se puede agregar en SQL de forma portable (Oracle / PostgreSQL / SQLite): se
traen solo las citas atendidas del período y se cuentan en Python.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import false, func, select, true
from sqlalchemy.orm import Session

from app.domain.enums import EstadoCaso, EstadoRegistroPaciente
from app.domain.enums_alertas import EstadoAlerta
from app.domain.enums_ept import EstadoEpt
from app.domain.enums_licencia import EstadoEnvioISL
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.alertas import AlertaNotif
from app.models.control_medico import ControlMedico
from app.models.ept import CasoEpt
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemCita
from app.schemas.reportes import ConteoEtiqueta, DashboardOperativo, PuntoTendencia

PERIODO_DEFECTO_DIAS = 30
DIAS_ODA_POR_VENCER = 15
DIAS_AGENDA_PROXIMA = 7
SEMANAS_TENDENCIA_MIN = 8
SEMANAS_TENDENCIA_MAX = 26
TOP_RANKING = 8

_ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
_NO_ASISTE = int(EstadoCitaSalutem.NO_ASISTE)
_ANULADO = int(EstadoCitaSalutem.ANULADO)
_NO_VIGENTES = (_ANULADO, _NO_ASISTE, _ATENDIDO)


class PeriodoInvalido(ValueError):
    """El período efectivo (con los valores por defecto ya aplicados) quedó invertido."""


def _contar(db: Session, stmt) -> int:
    return db.execute(stmt).scalar_one()


def _citas_vivas():
    return SalutemCita.desaparecida_en.is_(None)


def _contar_citas(db: Session, estado: int, desde: date, hasta: date) -> int:
    return _contar(
        db,
        select(func.count()).select_from(SalutemCita).where(
            _citas_vivas(),
            SalutemCita.estado_id == estado,
            SalutemCita.fecha_cita >= desde,
            SalutemCita.fecha_cita <= hasta,
        ),
    )


def _texto(valor: object, defecto: str) -> str:
    s = str(valor or "").strip()
    return s or defecto


def _ranking(contador: Counter[str]) -> list[ConteoEtiqueta]:
    return [ConteoEtiqueta(etiqueta=k, total=v) for k, v in contador.most_common(TOP_RANKING)]


def _lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _tendencia(db: Session, desde: date, hasta: date) -> list[PuntoTendencia]:
    """Atendidas vs. inasistencias por semana (lunes a domingo).

    Cubre las semanas del período, con un mínimo de 8 (un período corto igual muestra
    contexto) y un máximo de 26 (las últimas, para períodos largos).
    """
    ultima = _lunes(hasta)
    n = (ultima - _lunes(desde)).days // 7 + 1
    n = max(SEMANAS_TENDENCIA_MIN, min(SEMANAS_TENDENCIA_MAX, n))
    primera = ultima - timedelta(weeks=n - 1)
    filas = db.execute(
        select(SalutemCita.fecha_cita, SalutemCita.estado_id).where(
            _citas_vivas(),
            SalutemCita.estado_id.in_((_ATENDIDO, _NO_ASISTE)),
            SalutemCita.fecha_cita >= primera,
            SalutemCita.fecha_cita <= hasta,
        )
    ).all()
    semanas = {primera + timedelta(weeks=i): [0, 0] for i in range(n)}
    for fecha, estado in filas:
        par = semanas.get(_lunes(fecha))
        if par is not None:
            par[0 if estado == _ATENDIDO else 1] += 1
    return [
        PuntoTendencia(semana=s, atendidas=a, inasistencias=i)
        for s, (a, i) in sorted(semanas.items())
    ]


def resumen_operativo(
    db: Session,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    hoy: date | None = None,
) -> DashboardOperativo:
    # Fecha operacional local, como el resto del sistema (ver reporte_odas).
    hoy = hoy or date.today()
    hasta = fecha_hasta or hoy
    desde = fecha_desde or (hasta - timedelta(days=PERIODO_DEFECTO_DIAS - 1))
    if desde > hasta:
        raise PeriodoInvalido(
            f"El período queda invertido: desde {desde.isoformat()} es posterior a hasta {hasta.isoformat()}"
        )

    # ── Casos ────────────────────────────────────────────────────────────────
    activo = Ingreso.estado == EstadoCaso.ACTIVO.value
    pacientes_activos = _contar(db, select(func.count()).select_from(Ingreso).where(activo))
    ingresos_periodo = _contar(
        db,
        select(func.count()).select_from(Ingreso).where(
            Ingreso.fecha_ingreso >= desde, Ingreso.fecha_ingreso <= hasta
        ),
    )
    altas_periodo = _contar(
        db,
        select(func.count()).select_from(Ingreso).where(
            Ingreso.fecha_alta.is_not(None),
            Ingreso.fecha_alta >= desde,
            Ingreso.fecha_alta <= hasta,
        ),
    )
    por_programa = db.execute(
        select(Ingreso.programa, func.count()).where(activo).group_by(Ingreso.programa)
    ).all()
    activos_por_programa = sorted(
        (ConteoEtiqueta(etiqueta=_texto(p, "Sin programa"), total=n) for p, n in por_programa),
        key=lambda c: (-c.total, c.etiqueta),
    )

    # ── Atenciones SALUTEM del período ───────────────────────────────────────
    atendidas_filas = db.execute(
        select(SalutemCita.contenido).where(
            _citas_vivas(),
            SalutemCita.estado_id == _ATENDIDO,
            SalutemCita.fecha_cita >= desde,
            SalutemCita.fecha_cita <= hasta,
        )
    ).scalars().all()
    especialidades: Counter[str] = Counter()
    profesionales: Counter[str] = Counter()
    for contenido in atendidas_filas:
        c = contenido or {}
        especialidades[_texto(c.get("especialidadNombre"), "Sin especialidad")] += 1
        profesionales[_texto(c.get("profesionalNombre"), "Sin profesional")] += 1
    atenciones = len(atendidas_filas)
    inasistencias = _contar_citas(db, _NO_ASISTE, desde, hasta)
    anulaciones = _contar_citas(db, _ANULADO, desde, hasta)
    con_resultado = atenciones + inasistencias
    tasa = round(inasistencias * 100 / con_resultado, 1) if con_resultado else None

    agendadas_proximas = _contar(
        db,
        select(func.count()).select_from(SalutemCita).where(
            _citas_vivas(),
            SalutemCita.estado_id.not_in(_NO_VIGENTES),
            SalutemCita.fecha_cita >= hoy,
            SalutemCita.fecha_cita < hoy + timedelta(days=DIAS_AGENDA_PROXIMA),
        ),
    )
    controles_periodo = _contar(
        db,
        select(func.count()).select_from(ControlMedico).where(
            ControlMedico.fecha_control >= desde, ControlMedico.fecha_control <= hasta
        ),
    )

    # ── Pendientes de gestión (estado a hoy, no dependen del período) ────────
    lm_vigente = LicenciaMedica.anulada == false()
    licencias_activas = _contar(
        db,
        select(func.count()).select_from(LicenciaMedica).where(
            lm_vigente, LicenciaMedica.fecha_inicio <= hoy, LicenciaMedica.fecha_termino >= hoy
        ),
    )
    licencias_pendientes_isl = _contar(
        db,
        select(func.count()).select_from(LicenciaMedica).where(
            lm_vigente, LicenciaMedica.envio_isl == EstadoEnvioISL.PENDIENTE.value
        ),
    )
    odas_activas = (
        select(func.count())
        .select_from(Oda)
        .join(Ingreso, Oda.ingreso_id == Ingreso.id)
        .where(Oda.vigente == true(), activo)
    )
    odas_vencidas = _contar(db, odas_activas.where(Oda.fecha_vencimiento < hoy))
    odas_por_vencer = _contar(
        db,
        odas_activas.where(
            Oda.fecha_vencimiento >= hoy,
            Oda.fecha_vencimiento <= hoy + timedelta(days=DIAS_ODA_POR_VENCER),
        ),
    )
    ept_abiertos = _contar(
        db, select(func.count()).select_from(CasoEpt).where(CasoEpt.estado == EstadoEpt.ABIERTO.value)
    )
    pendientes_folio = _contar(
        db,
        select(func.count()).select_from(Paciente).where(
            Paciente.estado_registro == EstadoRegistroPaciente.PENDIENTE_FOLIO.value
        ),
    )
    alertas = db.execute(
        select(AlertaNotif.tipo, func.count())
        .where(AlertaNotif.estado != EstadoAlerta.RESUELTA.value)
        .group_by(AlertaNotif.tipo)
    ).all()
    alertas_por_tipo = sorted(
        (ConteoEtiqueta(etiqueta=t, total=n) for t, n in alertas), key=lambda c: (-c.total, c.etiqueta)
    )

    return DashboardOperativo(
        periodo_desde=desde,
        periodo_hasta=hasta,
        pacientes_activos=pacientes_activos,
        ingresos_periodo=ingresos_periodo,
        altas_periodo=altas_periodo,
        atenciones=atenciones,
        inasistencias=inasistencias,
        anulaciones=anulaciones,
        tasa_inasistencia=tasa,
        agendadas_proximas=agendadas_proximas,
        controles_periodo=controles_periodo,
        licencias_activas=licencias_activas,
        licencias_pendientes_isl=licencias_pendientes_isl,
        odas_vencidas=odas_vencidas,
        odas_por_vencer=odas_por_vencer,
        ept_abiertos=ept_abiertos,
        pacientes_pendientes_folio=pendientes_folio,
        alertas_abiertas=sum(c.total for c in alertas_por_tipo),
        alertas_por_tipo=alertas_por_tipo,
        activos_por_programa=activos_por_programa,
        atenciones_por_especialidad=_ranking(especialidades),
        atenciones_por_profesional=_ranking(profesionales),
        tendencia_semanal=_tendencia(db, desde, hasta),
    )
