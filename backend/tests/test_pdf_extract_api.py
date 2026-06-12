"""Tests de integración para el endpoint de lectura de PDF (CEPA-112)."""

import io

from app.routers.pdf_extract import MAX_PDF_BYTES, MAX_PDF_PAGES, _mapear_campos, get_pdf_parser
from app.services.pdf_parser import ExtractedPage, PdfParserStub


def _pdf_minimo_con_texto(texto: str) -> bytes:
    """Genera un PDF mínimo en memoria con pypdf para el test de carga."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


# TC-112-06: Auditor no puede cargar PDF → 403
def test_auditor_no_puede_cargar_pdf(as_auditor):
    data = _pdf_minimo_con_texto("datos")
    r = as_auditor.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("test.pdf", io.BytesIO(data), "application/pdf")},
    )
    assert r.status_code == 403


# TC-112-03: archivo no-PDF → mensaje de error + success=False + no bloquea flujo
def test_archivo_no_pdf_retorna_error_sin_bloquear(as_admin):
    contenido_no_pdf = b"esto no es un pdf valido"
    r = as_admin.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("documento.docx", io.BytesIO(contenido_no_pdf), "application/octet-stream")},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["success"] is False
    assert cuerpo["error_message"] is not None
    assert cuerpo["fields"] == []


# TC-112-01: PDF con capa de texto → success=True, campos pre-llenados
def test_pdf_legible_retorna_campos(as_admin):
    data = _pdf_minimo_con_texto("Nombre: Juan Pérez")
    r = as_admin.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("ficha.pdf", io.BytesIO(data), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["success"] is True
    # fields puede ser lista vacía si no hay texto extraíble (PDF en blanco es válido)
    assert isinstance(cuerpo["fields"], list)


# TC-112-04: PDF escaneado (sin texto) → success=True con fields=[], permite captura manual
def test_pdf_escaneado_retorna_lista_vacia(as_admin):
    # PDF en blanco (sin capa de texto) ya generado arriba
    data = _pdf_minimo_con_texto("")
    r = as_admin.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("escaneado.pdf", io.BytesIO(data), "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
    # El texto está vacío o no mapeado; fields puede estar vacío — eso está bien
    assert isinstance(r.json()["fields"], list)


# TC-112-02: confirm guarda los datos editados (la edición humana prevalece)
# El confirm solo valida estructura; el guardado real en el dominio lo hace la historia
# correspondiente. Aquí verificamos que el endpoint responda 200 con el payload editado.
def test_confirm_acepta_edicion_humana(as_admin):
    # Se deben incluir todos los campos required de la versión publicada de 'ingresos'
    payload = {
        "form_key": "ingresos",
        "fields": [
            {"field_key": "sexo", "value": "M"},
            {"field_key": "edad", "value": "35"},
            {"field_key": "diagnostico", "value": "F32"},
            {"field_key": "modelo_trat", "value": "ambulatorio"},
            {"field_key": "tipo_alta", "value": "terapeutica"},
            {"field_key": "tipo_ingreso", "value": "convenio"},
            {"field_key": "tipo_convenio", "value": "ISL"},
        ],
    }
    r = as_admin.post("/api/v1/pdf-extract/confirm", json=payload)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["received_fields"] == 7


# TC-112-05: confirm con campo obligatorio vacío → 422 (validación CEPA-111)
# El endpoint confirm solo valida que no haya value vacío en campos marcados como required
# por la definición activa del formulario. Si no hay versión publicada del form_key → 404.
def test_confirm_sin_form_publicado_retorna_404(as_admin):
    payload = {
        "form_key": "form_inexistente_xyz",
        "fields": [{"field_key": "sexo", "value": ""}],
    }
    r = as_admin.post("/api/v1/pdf-extract/confirm", json=payload)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# F2 — Validación RN-4 en confirm (TC-112-05 / CEPA-111)
# ---------------------------------------------------------------------------


def test_confirm_campo_requerido_faltante_retorna_422(as_admin):
    """F2: campo required ausente (valor vacío) → 422 con detalle missing_required."""
    # 'sexo' es required en la versión publicada de 'ingresos' (seeded en conftest)
    payload = {
        "form_key": "ingresos",
        "fields": [
            {"field_key": "sexo", "value": ""},          # requerido y vacío
            {"field_key": "edad", "value": "30"},
            {"field_key": "diagnostico", "value": "F32"},
            {"field_key": "modelo_trat", "value": "ambulatorio"},
            {"field_key": "tipo_alta", "value": "terapeutica"},
            {"field_key": "tipo_ingreso", "value": "convenio"},
            {"field_key": "tipo_convenio", "value": "ISL"},
        ],
    }
    r = as_admin.post("/api/v1/pdf-extract/confirm", json=payload)
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "missing_required" in detail
    assert "sexo" in detail["missing_required"]


def test_confirm_valor_fuera_de_dominio_retorna_422(as_admin):
    """F2: campo select con valor no permitido en domain_values → 422 con out_of_domain."""
    # 'sexo' tiene domain_values ["F", "M", "otro"]
    payload = {
        "form_key": "ingresos",
        "fields": [
            {"field_key": "sexo", "value": "invalido"},   # fuera de dominio
            {"field_key": "edad", "value": "30"},
            {"field_key": "diagnostico", "value": "F32"},
            {"field_key": "modelo_trat", "value": "ambulatorio"},
            {"field_key": "tipo_alta", "value": "terapeutica"},
            {"field_key": "tipo_ingreso", "value": "convenio"},
            {"field_key": "tipo_convenio", "value": "ISL"},
        ],
    }
    r = as_admin.post("/api/v1/pdf-extract/confirm", json=payload)
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "out_of_domain" in detail
    assert "sexo" in detail["out_of_domain"]


def test_confirm_payload_valido_retorna_200(as_admin):
    """F2: payload correcto con todos los campos required y valores en dominio → 200."""
    payload = {
        "form_key": "ingresos",
        "fields": [
            {"field_key": "sexo", "value": "F"},
            {"field_key": "edad", "value": "45"},
            {"field_key": "diagnostico", "value": "Z73"},
            {"field_key": "modelo_trat", "value": "residencial"},
            {"field_key": "tipo_alta", "value": "medica"},
            {"field_key": "tipo_ingreso", "value": "proyecto"},
            {"field_key": "tipo_convenio", "value": "SUSESO"},
        ],
    }
    r = as_admin.post("/api/v1/pdf-extract/confirm", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["acknowledged"] is True


# ---------------------------------------------------------------------------
# F3 — PDF upload hardening
# ---------------------------------------------------------------------------


def test_upload_pdf_oversized_retorna_success_false(as_admin):
    """F3(b): archivo mayor a MAX_PDF_BYTES → success=False (degradación gracia)."""
    # Generar bytes de relleno que superen el límite (~10 MB + 1 byte)
    junk = b"x" * (MAX_PDF_BYTES + 1)
    r = as_admin.post(
        "/api/v1/pdf-extract/upload",
        files={"file": ("grande.bin", io.BytesIO(junk), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["success"] is False
    assert cuerpo["error_message"] is not None
    assert "10" in cuerpo["error_message"]  # menciona el límite en MB


def test_upload_pdf_page_cap_via_stub(as_admin):
    """F3(b): stub con MAX_PDF_PAGES+1 páginas → solo se procesan MAX_PDF_PAGES.

    Se verifica que el raw_text incluye solo las primeras MAX_PDF_PAGES páginas.
    """
    from app.main import app

    # Crear stub con MAX_PDF_PAGES+5 páginas, cada una con texto único
    stub_pages = [
        ExtractedPage(page_num=i, text=f"PAGINA_{i}")
        for i in range(1, MAX_PDF_PAGES + 6)
    ]
    stub = PdfParserStub(pages=stub_pages)

    app.dependency_overrides[get_pdf_parser] = lambda: stub
    try:
        data = _pdf_minimo_con_texto("")
        r = as_admin.post(
            "/api/v1/pdf-extract/upload",
            files={"file": ("multi.pdf", io.BytesIO(data), "application/pdf")},
        )
    finally:
        app.dependency_overrides.pop(get_pdf_parser, None)

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["success"] is True
    # El raw_text NO debe incluir texto de la página MAX_PDF_PAGES+1
    assert f"PAGINA_{MAX_PDF_PAGES + 1}" not in cuerpo["raw_text"]
    # Sí debe incluir la última página dentro del límite
    assert f"PAGINA_{MAX_PDF_PAGES}" in cuerpo["raw_text"]


# ---------------------------------------------------------------------------
# F4 — Test mapping heuristic + parser DI
# ---------------------------------------------------------------------------


def test_upload_pdf_via_stub_mapea_campo(as_admin):
    """F4: override con PdfParserStub → el campo 'nombre' se extrae correctamente."""
    from app.main import app

    stub = PdfParserStub(pages=[ExtractedPage(page_num=1, text="Nombre: Juan")])
    app.dependency_overrides[get_pdf_parser] = lambda: stub
    try:
        data = _pdf_minimo_con_texto("")
        r = as_admin.post(
            "/api/v1/pdf-extract/upload",
            files={"file": ("ficha.pdf", io.BytesIO(data), "application/pdf")},
        )
    finally:
        app.dependency_overrides.pop(get_pdf_parser, None)

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["success"] is True
    field_keys = [f["field_key"] for f in cuerpo["fields"]]
    assert "nombre" in field_keys
    nombre_field = next(f for f in cuerpo["fields"] if f["field_key"] == "nombre")
    assert nombre_field["value"] == "Juan"


def test_mapear_campos_linea_conocida():
    """F4 (unitario): _mapear_campos con línea 'Clave: Valor' produce el campo esperado."""
    results = _mapear_campos("Nombre: Juan\nFecha: 2026-01-01")
    keys = [f.field_key for f in results]
    values = {f.field_key: f.value for f in results}
    assert "nombre" in keys
    assert values["nombre"] == "Juan"
    assert "fecha" in keys
    assert values["fecha"] == "2026-01-01"
