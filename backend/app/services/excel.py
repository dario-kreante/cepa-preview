"""Planillas Excel de los reportes, con el mismo formato en todos (QA 23-11-2026, QA-005).

Encabezados legibles en negrita, primera fila inmovilizada, filtros activos, fechas en
dd-mm-aaaa, booleanos como «Sí»/«No» y textos protegidos contra fórmulas (RUT y folio
quedan como texto).
"""

import io
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SIN_DATO = "—"
_FORMATO_FECHA = "DD-MM-YYYY"
_RELLENO_ENCABEZADO = PatternFill("solid", fgColor="DCE9E6")


def texto_seguro(valor: str) -> str:
    """Evita la inyección de fórmulas: un texto que parte con = + - @ (o tab/CR) se antepone con '."""
    return "'" + valor if valor[:1] in ("=", "+", "-", "@", "\t", "\r") else valor


def _celda(valor: Any) -> Any:
    if valor is None or valor == "":
        return SIN_DATO
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    if isinstance(valor, (date, int, float)):
        return valor
    return texto_seguro(str(valor))


def planilla(
    titulo: str,
    encabezados: Sequence[str],
    filas: Iterable[Sequence[Any]],
    anchos: Sequence[int] | None = None,
) -> bytes:
    """Una hoja con encabezados, filtros y la primera fila inmovilizada. Devuelve el .xlsx."""
    wb = Workbook()
    ws = wb.active
    ws.title = titulo[:31]
    ws.append(list(encabezados))
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = _RELLENO_ENCABEZADO
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for fila in filas:
        ws.append([_celda(v) for v in fila])
    for fila in ws.iter_rows(min_row=2):
        for c in fila:
            if isinstance(c.value, (date, datetime)):
                c.number_format = _FORMATO_FECHA
    ultima = get_column_letter(len(encabezados))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{ultima}{max(ws.max_row, 1)}"
    for i, titulo_col in enumerate(encabezados, start=1):
        ancho = anchos[i - 1] if anchos and i <= len(anchos) else max(12, len(titulo_col) + 4)
        ws.column_dimensions[get_column_letter(i)].width = ancho
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
