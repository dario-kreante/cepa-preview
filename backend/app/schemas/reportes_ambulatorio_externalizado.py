"""Schemas de los reportes «Ambulatorio» y «Externalizado» (QA del 23-11-2026)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class AmbulatorioItem(BaseModel):
    cita_id: int
    region: str | None
    codigo_region: str | None
    comuna: str | None
    codigo_comuna: str | None
    numero_cuenta: str | None
    opa: str | None
    oda: str | None
    rut: str | None
    nombre: str
    cantidad: int
    codigo_prestacion: str | None
    glosa_prestacion: str | None
    fecha: date
    hora: str | None
    monto_neto: int | None
    iva: int | None
    monto_total: int | None
    folio: str
    programa: str | None


class ReporteAmbulatorioResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total: int
    items: list[AmbulatorioItem]


ClasificacionFarmaco = Literal["Convenio 001", "Convenio 002", "Fuera de convenio", "REVISAR"]


class FarmacoConvenioItem(BaseModel):
    origen: Literal["Receta", "Esquema"]
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
    clasificacion: ClasificacionFarmaco
    detalle: str
    coincidencias: list[str]


class ResumenClasificacion(BaseModel):
    clasificacion: ClasificacionFarmaco
    total: int


class ReporteFarmacosConvenioResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total: int
    resumen: list[ResumenClasificacion]
    items: list[FarmacoConvenioItem]
