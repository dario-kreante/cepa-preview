"""Reporte «Ambulatorio» en el formato de la plataforma ISL (QA del 23-11-2026).

La clienta pidió agregar «región», «código región», «comuna» y «código comuna» al reporte de
SIGE. SIGE arma el reporte de atenciones con las columnas de la planilla de la plataforma ISL
(REGION, COMUNA, NUMERO DE CUENTA, OPA, ODA, RUT_BENEFICIARIO, …) con lo que sabe:

- Una fila por atención realizada (cita ``realizada``) en el período, de pacientes con ingreso.
- Región / comuna y sus códigos CUT (``app.domain.comunas``). El código de región sale de la
  comuna si se conoce; si no, de la región del paciente.
- OPA / ODA: la orden de SIGE que cubre la fecha de la atención (misma regla que el cruce de
  cobertura del reporte de ODA), en la columna que corresponde a su tipo.
- Código y glosa de la prestación: las prestaciones de la cita en SALUTEM
  (``salutem_cita.contenido.prestaciones``: ``codigo`` y ``nombre``). Son los códigos internos de
  SALUTEM, no los del arancel ISL. Sin prestaciones, la glosa es la especialidad.
- Hora: la hora de inicio de la cita en SALUTEM.
- N° de cuenta y montos: SIGE no los tiene; quedan vacíos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendamiento.salutem import lotes
from app.domain.comunas import REGIONES, buscar_comuna, codigo_region
from app.models.cita import Cita
from app.models.ingreso import Ingreso
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemCita
from app.services.cobertura_oda import oda_que_cubre
from app.services.excel import planilla
from app.services.reporte_odas import aplicar_programa, tipo_visible

SEPARADOR = " / "


@dataclass
class FilaAmbulatorio:
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


def _texto(valor) -> str | None:
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def _hora(contenido: dict | None) -> str | None:
    """«09:00:00» → «09:00». `/cita` usa citaHoraInicio; `/atencion`, citaHorarioInicio."""
    contenido = contenido or {}
    hora = _texto(contenido.get("citaHoraInicio") or contenido.get("citaHorarioInicio"))
    return hora[:5] if hora else None


def prestaciones_de(contenido: dict | None) -> list[tuple[str | None, str | None]]:
    """(código, nombre) de cada prestación de la cita de SALUTEM, sin repetir."""
    crudas = (contenido or {}).get("prestaciones")
    if not isinstance(crudas, list):
        return []
    vistas: dict[tuple[str | None, str | None], None] = {}
    for p in crudas:
        if not isinstance(p, dict):
            continue
        codigo = _texto(p.get("codigo"))
        nombre = _texto(p.get("nombre") or p.get("glosa"))
        if codigo or nombre:
            vistas[(codigo, nombre)] = None
    return list(vistas)


def _ubicacion(p: Paciente) -> tuple[str | None, str | None, str | None, str | None]:
    """(región, código región, comuna, código comuna)."""
    comuna = buscar_comuna(p.comuna)
    if comuna is not None:
        cod_comuna, nombre, cod_region = comuna
        return REGIONES[cod_region], cod_region, nombre, cod_comuna
    return p.region, codigo_region(p.region), _texto(p.comuna), None


def _unir(valores: list[str | None]) -> str | None:
    limpios = [v for v in valores if v]
    return SEPARADOR.join(limpios) if limpios else None


def construir_filas(
    db: Session,
    desde: date,
    hasta: date,
    *,
    programa: str | None = None,
    region: str | None = None,
) -> list[FilaAmbulatorio]:
    stmt = (
        select(Cita, Ingreso, Paciente)
        .join(Ingreso, Cita.ingreso_id == Ingreso.id)
        .join(Paciente, Ingreso.paciente_id == Paciente.id)
        .where(Cita.estado == "realizada", Cita.fecha >= desde, Cita.fecha <= hasta)
    )
    stmt = aplicar_programa(stmt, programa)
    if region is not None:
        stmt = stmt.where(Paciente.region == region)
    filas = db.execute(stmt.order_by(Cita.fecha.asc(), Paciente.nombre.asc(), Cita.id.asc())).all()
    if not filas:
        return []

    # Órdenes de todos los ingresos de cada paciente: la ODA puede estar en otro folio.
    paciente_ids = {p.id for _, _, p in filas}
    odas: dict[int, list[Oda]] = defaultdict(list)
    for lote in lotes(paciente_ids):  # Oracle: máximo 1000 valores por IN
        for oda, pid in db.execute(
            select(Oda, Ingreso.paciente_id)
            .join(Ingreso, Oda.ingreso_id == Ingreso.id)
            .where(Ingreso.paciente_id.in_(lote))
        ).all():
            odas[pid].append(oda)

    salutem_ids = {c.salutem_cita_id for c, _, _ in filas if c.salutem_cita_id is not None}
    contenido_cita: dict[int, dict] = {}
    contenido_atencion: dict[int, dict] = {}
    for lote in lotes(salutem_ids):
        for cid, contenido in db.execute(
            select(SalutemCita.cita_id, SalutemCita.contenido).where(SalutemCita.cita_id.in_(lote))
        ).all():
            contenido_cita[cid] = contenido or {}
        for cid, contenido in db.execute(
            select(SalutemAtencion.cita_id, SalutemAtencion.contenido).where(
                SalutemAtencion.cita_id.in_(lote)
            )
        ).all():
            contenido_atencion[cid] = contenido or {}

    resultado: list[FilaAmbulatorio] = []
    for cita, ing, pac in filas:
        region_nombre, cod_region, comuna, cod_comuna = _ubicacion(pac)
        orden = oda_que_cubre(odas.get(pac.id, []), cita.fecha)
        opa = oda = None
        if orden is not None:
            if tipo_visible(orden.tipo_orden) == "OPA":
                opa = orden.identificador
            else:
                oda = orden.identificador

        c_cita = contenido_cita.get(cita.salutem_cita_id or -1)
        c_atencion = contenido_atencion.get(cita.salutem_cita_id or -1)
        prestaciones = prestaciones_de(c_cita) or prestaciones_de(c_atencion)
        if prestaciones:
            codigo = _unir([c for c, _ in prestaciones])
            glosa = _unir([n for _, n in prestaciones])
        else:
            codigo = None
            glosa = _texto(cita.especialidad) or _texto(ing.especialidad)

        resultado.append(
            FilaAmbulatorio(
                cita_id=cita.id,
                region=region_nombre,
                codigo_region=cod_region,
                comuna=comuna,
                codigo_comuna=cod_comuna,
                numero_cuenta=None,
                opa=opa,
                oda=oda,
                rut=pac.rut,
                nombre=pac.nombre,
                cantidad=1,
                codigo_prestacion=codigo,
                glosa_prestacion=glosa,
                fecha=cita.fecha,
                hora=_hora(c_cita) or _hora(c_atencion),
                monto_neto=None,
                iva=None,
                monto_total=None,
                folio=ing.folio,
                programa=ing.programa,
            )
        )
    resultado.sort(key=lambda f: (f.fecha, f.hora or "", f.nombre, f.cita_id))
    return resultado


# ── Excel ──────────────────────────────────────────────────────────────────────

ENCABEZADOS_EXCEL = (
    "Región", "Código región", "Comuna", "Código comuna", "N° cuenta", "OPA", "ODA", "RUT",
    "Nombre", "Cantidad", "Código prestación", "Glosa prestación", "Fecha", "Hora",
    "Monto neto", "IVA", "Monto total", "Folio", "Programa",
)


def _codigo_numerico(codigo: str | None) -> int | str | None:
    """Los códigos CUT van como número en la planilla del ISL (9 y 9101, no «09» ni «09101»)."""
    return int(codigo) if codigo and codigo.isdigit() else codigo


def generar_excel(filas: list[FilaAmbulatorio]) -> bytes:
    return planilla(
        "Ambulatorio",
        ENCABEZADOS_EXCEL,
        (
            [
                f.region, _codigo_numerico(f.codigo_region), f.comuna,
                _codigo_numerico(f.codigo_comuna), f.numero_cuenta, f.opa, f.oda, f.rut,
                f.nombre, f.cantidad, f.codigo_prestacion, f.glosa_prestacion, f.fecha, f.hora,
                f.monto_neto, f.iva, f.monto_total, f.folio, f.programa,
            ]
            for f in filas
        ),
        anchos=(16, 10, 18, 10, 12, 12, 12, 14, 32, 9, 14, 34, 12, 8, 11, 9, 11, 14, 18),
    )
