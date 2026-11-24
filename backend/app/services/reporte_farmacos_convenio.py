"""Reporte «Externalizado» de fármacos (QA-010 / QA-013).

Cada fármaco recetado en el período, con el paciente y su clasificación frente a la canasta
del Convenio 002 y la lista Externalizado (``app.domain.farmacos_convenio``):

- Recetas (``receta``): la marca/medicamento de la receta, por fecha de emisión.
- Esquema (``esquema_indicacion``): cada medicamento indicado, por fecha de registro.

SIGE guarda el fármaco como texto libre y sin código SAP; el código SAP que muestra el reporte
es el de la canasta cuando la coincidencia es única.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.farmacos_convenio import Clasificador, ItemCanasta, ItemExternalizado
from app.models.farmaco_convenio import FarmacoCanasta, FarmacoExternalizado
from app.models.farmacos import EsquemaIndicacion, Receta, RegistroFarmacologico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.services.excel import planilla

_SANTIAGO = ZoneInfo("America/Santiago")
SEPARADOR = " / "

Origen = Literal["Receta", "Esquema"]


@dataclass
class FilaFarmaco:
    origen: Origen
    registro_id: int
    fecha: date
    paciente_id: int
    paciente_nombre: str
    paciente_rut: str | None
    folio: str
    ingreso_id: int
    programa: str | None
    farmaco: str
    dosis: str | None
    codigo_sap: str | None
    clasificacion: str
    detalle: str
    coincidencias: list[str]


def cargar_clasificador(db: Session) -> Clasificador:
    canasta = [
        ItemCanasta(c.codigo_sap, c.descripcion, c.principio_activo, c.marca)
        for c in db.scalars(select(FarmacoCanasta).order_by(FarmacoCanasta.id))
    ]
    externalizado = [
        ItemExternalizado(e.glosa, e.convenio_001, e.convenio_002)
        for e in db.scalars(select(FarmacoExternalizado).order_by(FarmacoExternalizado.id))
    ]
    return Clasificador(canasta, externalizado)


def _limites_utc(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """Días completos en hora de Chile, en UTC (el driver de Oracle puede descartar la zona)."""
    inicio = datetime.combine(desde, time.min, tzinfo=_SANTIAGO).astimezone(timezone.utc)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=_SANTIAGO).astimezone(timezone.utc)
    return inicio, fin


def _fecha_local(valor: datetime) -> date:
    # Oracle devuelve la fecha sin zona: se guardó en UTC.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(_SANTIAGO).date()


def construir_filas(
    db: Session, desde: date, hasta: date, *, paciente_id: int | None = None
) -> list[FilaFarmaco]:
    clasificador = cargar_clasificador(db)
    base = (
        select(RegistroFarmacologico.id, Ingreso, Paciente)
        .join(Ingreso, RegistroFarmacologico.ingreso_id == Ingreso.id)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
    )
    if paciente_id is not None:
        base = base.where(Paciente.id == paciente_id)

    filas: list[FilaFarmaco] = []

    def agregar(origen: Origen, reg_id: int, fecha: date, ing: Ingreso, pac: Paciente,
                farmaco: str, dosis: str | None) -> None:
        r = clasificador.clasificar(farmaco)
        filas.append(
            FilaFarmaco(
                origen=origen, registro_id=reg_id, fecha=fecha, paciente_id=pac.id,
                paciente_nombre=pac.nombre, paciente_rut=pac.rut, folio=ing.folio,
                ingreso_id=ing.id, programa=ing.programa, farmaco=farmaco, dosis=dosis,
                codigo_sap=r.codigo_sap, clasificacion=r.clasificacion, detalle=r.detalle,
                coincidencias=list(r.coincidencias),
            )
        )

    recetas = db.execute(
        base.add_columns(Receta)
        .join(Receta, Receta.registro_id == RegistroFarmacologico.id)
        .where(Receta.fecha_emision >= desde, Receta.fecha_emision <= hasta)
    ).all()
    for _reg_id, ing, pac, receta in recetas:
        agregar("Receta", receta.id, receta.fecha_emision, ing, pac, receta.marca_medicamento, None)

    inicio, fin = _limites_utc(desde, hasta)
    indicaciones = db.execute(
        base.add_columns(EsquemaIndicacion)
        .join(EsquemaIndicacion, EsquemaIndicacion.registro_id == RegistroFarmacologico.id)
        .where(EsquemaIndicacion.created_at >= inicio, EsquemaIndicacion.created_at < fin)
    ).all()
    for _reg_id, ing, pac, ind in indicaciones:
        dosis = SEPARADOR.join(x for x in (ind.dosis, ind.frecuencia) if x) or None
        agregar("Esquema", ind.id, _fecha_local(ind.created_at), ing, pac, ind.medicamento, dosis)

    filas.sort(key=lambda f: (f.fecha, f.paciente_nombre, f.origen, f.registro_id))
    return filas


# ── Excel ──────────────────────────────────────────────────────────────────────

ENCABEZADOS_EXCEL = (
    "Fecha", "Paciente", "RUT", "Folio", "Programa", "Origen", "Fármaco", "Dosis",
    "Código SAP", "Clasificación", "Detalle", "Coincide con",
)


def generar_excel(filas: list[FilaFarmaco]) -> bytes:
    return planilla(
        "Externalizado",
        ENCABEZADOS_EXCEL,
        (
            [
                f.fecha, f.paciente_nombre, f.paciente_rut, f.folio, f.programa, f.origen,
                f.farmaco, f.dosis, f.codigo_sap, f.clasificacion, f.detalle,
                SEPARADOR.join(f.coincidencias),
            ]
            for f in filas
        ),
        anchos=(12, 30, 14, 14, 18, 10, 30, 18, 11, 18, 48, 48),
    )
