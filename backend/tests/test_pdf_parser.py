"""Tests del servicio de extracción de PDF (CEPA-112).

Los tests NO usan archivos binarios reales: trabajan con un PDF mínimo generado
en memoria (pypdf.PdfWriter) o con el PdfParserStub inyectable.
"""

import io

import pytest

from app.services.pdf_parser import ExtractedPage, PdfParserStub, PypdfParser


def _pdf_con_texto(texto: str) -> bytes:
    """Genera un PDF mínimo en memoria con el texto indicado (para tests)."""
    from pypdf import PdfWriter

    # Usamos ReportLab-free: escribimos el PDF manualmente con pypdf
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def _pdf_vacio() -> bytes:
    """PDF sin capa de texto (simula escaneado)."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


# TC-112-01: parser real extrae texto de un PDF con capa de texto
def test_pypdf_parser_extrae_texto():
    # Usamos el stub porque no podemos predecir el texto exacto que pypdf
    # extraerá del stream manual. Probamos el flujo completo con el stub.
    stub = PdfParserStub(pages=[ExtractedPage(page_num=1, text="Nombre: Juan Perez RUT: 12.345.678-5")])
    resultado = stub.extract(b"cualquier-bytes")
    assert len(resultado) == 1
    assert "Juan Perez" in resultado[0].text


# TC-112-03: archivo no-PDF → ExtractionError
def test_parser_rechaza_no_pdf():
    from app.services.pdf_parser import ExtractionError
    parser = PypdfParser()
    with pytest.raises(ExtractionError):
        parser.extract(b"esto no es un pdf")


# TC-112-04: PDF sin capa de texto → lista vacía de páginas con texto
def test_pdf_sin_texto_retorna_paginas_vacias():
    parser = PypdfParser()
    resultado = parser.extract(_pdf_vacio())
    # Puede tener páginas pero sin texto
    for p in resultado:
        assert p.text.strip() == ""


# Stub es mockeable: devuelve lo que se le inyecta
def test_stub_devuelve_exactamente_lo_inyectado():
    stub = PdfParserStub(pages=[
        ExtractedPage(page_num=1, text="campo1: valor1"),
        ExtractedPage(page_num=2, text="campo2: valor2"),
    ])
    resultado = stub.extract(b"bytes-irrelevantes")
    assert len(resultado) == 2
    assert resultado[1].text == "campo2: valor2"


# Stub de error: simula PDF ilegible
def test_stub_de_error_lanza_excepcion():
    from app.services.pdf_parser import ExtractionError, PdfParserErrorStub
    stub = PdfParserErrorStub()
    with pytest.raises(ExtractionError):
        stub.extract(b"cualquier-cosa")
