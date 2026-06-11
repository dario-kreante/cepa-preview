"""Abstracción de extracción de texto de PDF (CEPA-112).

Usa el patrón Protocol (duck-typing) para permitir la inyección de dependencias
en tests sin depender de archivos binarios reales.

Clases exportadas:
- ExtractedPage      — valor simple (dataclass): página con texto extraído.
- PdfParser          — Protocol; cualquier clase con método extract() lo implementa.
- PypdfParser        — implementación real con pypdf.
- PdfParserStub      — stub para tests: devuelve páginas predefinidas.
- PdfParserErrorStub — stub que lanza ExtractionError (simula PDF ilegible).
- ExtractionError    — excepción base de este módulo.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ExtractionError(Exception):
    """Se lanza cuando el archivo no es un PDF válido o es ilegible."""


@dataclass
class ExtractedPage:
    page_num: int
    text: str


@runtime_checkable
class PdfParser(Protocol):
    """Protocol inyectable. Cualquier clase con este método es un PdfParser."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]: ...


class PypdfParser:
    """Implementación real con pypdf (sin dependencias de sistema operativo)."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            raise ExtractionError(f"No se pudo leer el PDF: {exc}") from exc

        pages: list[ExtractedPage] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(ExtractedPage(page_num=i, text=text))
        return pages


class PdfParserStub:
    """Stub determinista para tests. Devuelve páginas fijas independientemente del input."""

    def __init__(self, pages: list[ExtractedPage] | None = None) -> None:
        self._pages: list[ExtractedPage] = pages or []

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]:
        return self._pages


class PdfParserErrorStub:
    """Stub que siempre falla. Simula PDF ilegible/escaneado sin texto (TC-112-04)."""

    def extract(self, pdf_bytes: bytes) -> list[ExtractedPage]:
        raise ExtractionError("PDF ilegible: sin capa de texto (stub de error).")
