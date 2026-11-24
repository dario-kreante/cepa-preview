"""Reporte de ODA (QA-006 / QA-007, registro de pruebas del 16-11-2026).

- ``construir_filas_vencidas``: ODA vencidas con el cruce de cobertura del anexo de la clienta,
  más los pacientes atendidos que no tienen ninguna orden (también SOLICITAR).
- ``listar_estado_odas``: listado por paciente con el estado del caso y de la ODA.
- ``generar_excel``: la misma tabla de vencidas en xlsx.

Cruce de cobertura (una fila por paciente). Las órdenes son las ODA/OPA del reporte ISL
(«Ambulatoria» = ODA; «OPA»/«OPAEP» = OPA). Para cada fecha de atención (citas realizadas)
se revisa si cae entre el inicio y el término de alguna orden del paciente:
CUBRE = todas las atenciones tienen una orden vigente ese día; SOLICITAR = alguna no la
tiene. Sin atenciones se evalúa hoy: una orden vencida no cubre, así que queda SOLICITAR.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from sqlalchemy import and_, func, select, true
from sqlalchemy.orm import Session, aliased

from app.agendamiento.salutem import lotes
from app.domain.enums import EstadoCaso
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.services.cobertura_oda import oda_que_cubre, odas_por_ingreso
from app.services.dashboard_operativo import DIAS_ODA_POR_VENCER
from app.services.excel import planilla

ESTADOS_GESTION = ("pendiente", "solicitada", "recibida")
EstadoGestion = Literal["pendiente", "solicitada", "recibida"]
SEPARADOR = " / "
SIN_DATO = "—"

# El filtro del reporte usa estos nombres; Ingreso.programa es texto libre (el seed guarda
# «Programa Regular», «PIPT», «Ley Karin»), así que se compara sin mayúsculas y por fragmento.
_PROGRAMAS = {
    "regular": "%regular%",
    "ingreso_isl": "%ingreso isl%",
    "tratamiento_isl": "%tratamiento isl%",
    "ley_karin": "%karin%",
    "pipt": "%pipt%",
}


def tipo_visible(tipo_orden: str | None) -> str | None:
    """Ambulatoria → ODA; OPA / OPAEP → OPA; otro valor se muestra tal cual; sin dato → None."""
    if not tipo_orden:
        return None
    clave = tipo_orden.strip().lower()
    if clave == "ambulatoria":
        return "ODA"
    if clave in ("opa", "opaep"):
        return "OPA"
    return tipo_orden.strip()


def aplicar_programa(stmt, programa: str | None):
    if programa is None:
        return stmt
    patron = _PROGRAMAS.get(programa)
    if patron is not None:
        return stmt.where(func.lower(Ingreso.programa).like(patron))
    return stmt.where(Ingreso.programa == programa)


@dataclass
class OrdenFila:
    identificador: str
    tipo: str | None
    fecha_inicio: date | None
    fecha_termino: date


@dataclass
class FilaVencida:
    # La ODA vencida sobre la que se gestiona; None = paciente atendido sin ninguna orden.
    oda: Oda | None
    ingreso: Ingreso
    paciente: Paciente
    ordenes: list[OrdenFila] = field(default_factory=list)
    fechas_atencion: list[date] = field(default_factory=list)
    cobertura: Literal["CUBRE", "SOLICITAR"] = "SOLICITAR"
    # Todas las órdenes del paciente (para evaluar la cobertura) y sus ingresos.
    pool: list[Oda] = field(default_factory=list, repr=False)
    ingreso_ids: set[int] = field(default_factory=set, repr=False)


def construir_filas_vencidas(
    db: Session,
    hoy: date,
    *,
    programa: str | None = None,
    region: str | None = None,
    comuna: str | None = None,
) -> list[FilaVencida]:
    stmt = (
        select(Oda, Ingreso, Paciente)
        .join(Ingreso, Oda.ingreso_id == Ingreso.id)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .where(
            Oda.fecha_vencimiento < hoy,
            # `== true()` y no `.is_(True)`: Oracle rechaza "IS 1" (ORA-00908).
            Oda.vigente == true(),
            Ingreso.estado == EstadoCaso.ACTIVO.value,
        )
    )
    stmt = aplicar_programa(stmt, programa)
    if region is not None:
        stmt = stmt.where(Paciente.region == region)
    if comuna is not None:
        stmt = stmt.where(Paciente.comuna == comuna)
    rows = db.execute(stmt.order_by(Oda.fecha_vencimiento.asc(), Oda.id.asc())).all()

    # Una fila por paciente: se gestiona la ODA vencida más reciente.
    por_paciente: dict[int, list[tuple[Oda, Ingreso, Paciente]]] = defaultdict(list)
    for fila in rows:
        por_paciente[fila[2].id].append(fila)

    ingreso_ids = {ing.id for _, ing, _ in rows}
    odas = odas_por_ingreso(db, ingreso_ids)

    resultado: list[FilaVencida] = []
    desde_de: dict[int, date] = {}
    for pid, grupo in por_paciente.items():
        oda, ing, pac = grupo[-1]
        # Las atenciones relevantes empiezan donde empieza la orden vencida (si no se conoce
        # su inicio, donde terminó): lo anterior ya lo cubrían las órdenes previas.
        desde_de[pid] = min(o.fecha_registro or o.fecha_vencimiento for o, _, _ in grupo)
        ids = {g[1].id for g in grupo}
        pool = [o for i in ids for o in odas.get(i, [])]
        ordenes = sorted(
            (o for o in pool if o.fecha_vencimiento >= desde_de[pid]),
            key=lambda o: (o.fecha_registro or o.fecha_vencimiento, o.id),
        )
        resultado.append(
            FilaVencida(
                oda=oda,
                ingreso=ing,
                paciente=pac,
                ordenes=[
                    OrdenFila(o.identificador, tipo_visible(o.tipo_orden), o.fecha_registro, o.fecha_vencimiento)
                    for o in ordenes
                ],
                pool=pool,
                ingreso_ids=ids,
            )
        )

    if resultado:
        minimo = min(desde_de.values())
        fechas_por_ingreso: dict[int, set[date]] = defaultdict(set)
        for lote in lotes(ingreso_ids):  # Oracle: máximo 1000 valores por IN
            citas = db.execute(
                select(Cita.ingreso_id, Cita.fecha).where(
                    Cita.ingreso_id.in_(lote),
                    Cita.estado == "realizada",
                    Cita.fecha >= minimo,
                    Cita.fecha <= hoy,
                )
            ).all()
            for ingreso_id, fecha in citas:
                fechas_por_ingreso[ingreso_id].add(fecha)
        for fila in resultado:
            desde = desde_de[fila.paciente.id]
            fechas = sorted(
                {f for i in fila.ingreso_ids for f in fechas_por_ingreso.get(i, ()) if f >= desde}
            )
            fila.fechas_atencion = fechas
            a_revisar = fechas or [hoy]
            cubierto = all(oda_que_cubre(fila.pool, f) is not None for f in a_revisar)
            fila.cobertura = "CUBRE" if cubierto else "SOLICITAR"

    resultado.sort(key=lambda f: (f.oda.fecha_vencimiento, f.oda.id))
    resultado.extend(
        _filas_atendidos_sin_oda(db, hoy, programa=programa, region=region, comuna=comuna)
    )
    return resultado


def _filas_atendidos_sin_oda(
    db: Session,
    hoy: date,
    *,
    programa: str | None,
    region: str | None,
    comuna: str | None,
) -> list[FilaVencida]:
    """Pacientes con ingreso activo y alguna cita realizada, sin ninguna ODA/OPA registrada.

    El anexo de la clienta también pide SOLICITAR cuando el paciente fue atendido y no tiene
    orden en el reporte ISL. «Registrada» cuenta cualquier orden, en cualquiera de los ingresos
    del paciente, vigente o no: así no se duplica a quien ya aparece por una ODA vencida.
    """
    otro = aliased(Ingreso)
    con_orden = (
        select(Oda.id)
        .join(otro, Oda.ingreso_id == otro.id)
        .where(otro.paciente_id == Paciente.id)
        .exists()
    )
    realizada = (
        select(Cita.id)
        .where(Cita.ingreso_id == Ingreso.id, Cita.estado == "realizada", Cita.fecha <= hoy)
        .exists()
    )
    stmt = (
        select(Ingreso, Paciente)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .where(Ingreso.estado == EstadoCaso.ACTIVO.value, realizada, ~con_orden)
    )
    stmt = aplicar_programa(stmt, programa)
    if region is not None:
        stmt = stmt.where(Paciente.region == region)
    if comuna is not None:
        stmt = stmt.where(Paciente.comuna == comuna)
    rows = db.execute(stmt.order_by(Paciente.nombre.asc(), Ingreso.id.asc())).all()

    # Una fila por paciente: si tiene varios ingresos activos atendidos, el más reciente.
    por_paciente: dict[int, tuple[Ingreso, Paciente]] = {}
    for ing, pac in rows:
        por_paciente[pac.id] = (ing, pac)  # el id mayor queda al final
    if not por_paciente:
        return []

    ingreso_ids = {ing.id for ing, _ in por_paciente.values()}
    fechas_por_ingreso: dict[int, set[date]] = defaultdict(set)
    for lote in lotes(ingreso_ids):  # Oracle: máximo 1000 valores por IN
        citas = db.execute(
            select(Cita.ingreso_id, Cita.fecha).where(
                Cita.ingreso_id.in_(lote), Cita.estado == "realizada", Cita.fecha <= hoy
            )
        ).all()
        for ingreso_id, fecha in citas:
            fechas_por_ingreso[ingreso_id].add(fecha)

    return [
        FilaVencida(
            oda=None,
            ingreso=ing,
            paciente=pac,
            fechas_atencion=sorted(fechas_por_ingreso.get(ing.id, ())),
            cobertura="SOLICITAR",
        )
        for ing, pac in por_paciente.values()
    ]


# ── Excel ──────────────────────────────────────────────────────────────────────

ENCABEZADOS_EXCEL = (
    "Folio", "Nombre", "RUT", "Programa", "Región", "Comuna", "Fecha de atención",
    "N° ODA/OPA", "Tipo", "Fecha inicio", "Fecha término", "Cobertura", "Estado de gestión",
)


def _fecha(d: date | None) -> str:
    return d.strftime("%d-%m-%Y") if d else SIN_DATO


def _unir(valores: list[str]) -> str:
    return SEPARADOR.join(valores) if valores else SIN_DATO


def _ordenes_de(f: FilaVencida, dia: date | None) -> list[OrdenFila]:
    """Las órdenes cuyo período cubre la fecha de atención; si ninguna la cubre, todas."""
    if dia is None:
        return f.ordenes
    cubren = [
        o for o in f.ordenes
        if (o.fecha_inicio is None or o.fecha_inicio <= dia)
        and (o.fecha_termino is None or dia <= o.fecha_termino)
    ]
    return cubren or f.ordenes


def generar_excel(filas: list[FilaVencida]) -> bytes:
    """QA-006 (23-11-2026): una fila por fecha de atención (se repite el paciente), con
    folio, programa, región y comuna, para buscar cada atención con su N° de orden."""

    def filas_excel():
        for f in filas:
            for dia in f.fechas_atencion or [None]:
                ordenes = _ordenes_de(f, dia)
                yield [
                    f.ingreso.folio, f.paciente.nombre, f.paciente.rut, f.ingreso.programa,
                    f.paciente.region, f.paciente.comuna, dia,
                    _unir([o.identificador for o in ordenes]),
                    _unir([o.tipo or SIN_DATO for o in ordenes]),
                    _unir([_fecha(o.fecha_inicio) for o in ordenes]),
                    _unir([_fecha(o.fecha_termino) for o in ordenes]),
                    f.cobertura,
                    f.oda.estado_gestion.capitalize() if f.oda else None,
                ]

    return planilla(
        "ODA vencidas",
        ENCABEZADOS_EXCEL,
        filas_excel(),
        anchos=(14, 32, 14, 18, 16, 16, 14, 20, 10, 14, 14, 12, 18),
    )


# ── QA-006: listado por paciente ───────────────────────────────────────────────

EstadoOda = Literal["vigente", "por_vencer", "vencida", "sin_oda"]


@dataclass
class FilaEstado:
    ingreso: Ingreso
    paciente: Paciente
    oda: Oda | None
    estado_oda: EstadoOda
    dias_para_vencer: int | None


def listar_estado_odas(
    db: Session, hoy: date, *, estado_caso: str | None = None, programa: str | None = None
) -> list[FilaEstado]:
    stmt = (
        select(Ingreso, Paciente, Oda)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .outerjoin(Oda, and_(Oda.ingreso_id == Ingreso.id, Oda.vigente == true()))
    )
    if estado_caso is not None:
        stmt = stmt.where(Ingreso.estado == estado_caso)
    stmt = aplicar_programa(stmt, programa)
    rows = db.execute(stmt.order_by(Paciente.nombre.asc(), Ingreso.id.asc())).all()

    filas: list[FilaEstado] = []
    for ing, pac, oda in rows:
        if oda is None:
            filas.append(FilaEstado(ing, pac, None, "sin_oda", None))
            continue
        dias = (oda.fecha_vencimiento - hoy).days
        if dias < 0:
            estado: EstadoOda = "vencida"
        elif dias <= DIAS_ODA_POR_VENCER:
            estado = "por_vencer"
        else:
            estado = "vigente"
        filas.append(FilaEstado(ing, pac, oda, estado, dias))
    return filas
