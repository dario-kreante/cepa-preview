"""Schemas Pydantic v2 para el endpoint de extracción de PDF (CEPA-112)."""

from __future__ import annotations

from pydantic import BaseModel


class ExtractedFieldOut(BaseModel):
    """Campo extraído del PDF, pre-llenado y editable."""

    field_key: str
    value: str


class PdfExtractResult(BaseModel):
    """Resultado de la extracción: campos pre-llenados + metadatos."""

    success: bool
    # Texto crudo concatenado de todas las páginas (para debug / auditoría)
    raw_text: str
    # Lista de campos extraídos con nombre sugerido (mapeo heurístico básico)
    fields: list[ExtractedFieldOut]
    # Mensaje de error si success=False
    error_message: str | None = None


class PdfConfirmPayload(BaseModel):
    """Payload de confirmación: campos revisados/editados por el administrativo.

    La edición humana prevalece sobre la extracción (RN-1 / CA-2).
    El form_key indica qué formulario recibe los datos confirmados.
    """

    form_key: str
    fields: list[ExtractedFieldOut]
