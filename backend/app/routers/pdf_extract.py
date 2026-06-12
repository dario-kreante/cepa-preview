"""Router de lectura de documentos PDF (CEPA-112 P1).

El parser se inyecta vía dependencia FastAPI: en producción usa PypdfParser;
en tests se puede sobreescribir con un stub.

Degradación gracia (RN-3): si la extracción falla, devuelve success=False
con error_message y fields=[], sin bloquear el flujo de captura manual.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.pdf_extract import ExtractedFieldOut, PdfConfirmPayload, PdfExtractResult
from app.services.pdf_parser import ExtractionError, PdfParser, PypdfParser
from app.services import form_config as form_svc

router = APIRouter(prefix="/api/v1/pdf-extract", tags=["pdf-extract"])

# Límites de carga (F3 — PDF upload hardening)
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PDF_PAGES = 50  # se procesan las primeras 50 páginas; el resto se ignora

# Auditor es solo lectura — carga de PDF requiere rol escritor
_writer = require_role("Administrativo", "Coordinacion")


def get_pdf_parser() -> PdfParser:
    """Dependencia inyectable: en tests se sobreescribe con un stub."""
    return PypdfParser()


def _mapear_campos(raw_text: str) -> list[ExtractedFieldOut]:
    """Heurística simple de mapeo de texto a campos conocidos.

    Versión v1: busca patrones 'Clave: Valor' en el texto y mapea
    a field_key normalizados. En producción se puede extender con
    un mapeador configurable o regex por tipo de documento.
    """
    fields: list[ExtractedFieldOut] = []
    for line in raw_text.splitlines():
        if ":" in line:
            partes = line.split(":", 1)
            key_raw = partes[0].strip().lower().replace(" ", "_")
            value = partes[1].strip()
            if key_raw and value:
                fields.append(ExtractedFieldOut(field_key=key_raw, value=value))
    return fields


@router.post(
    "/upload",
    response_model=PdfExtractResult,
    dependencies=[Depends(_writer)],
)
async def upload_pdf(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    parser: PdfParser = Depends(get_pdf_parser),
) -> PdfExtractResult:
    """Recibe un PDF, extrae texto y devuelve campos pre-llenados (no persiste).

    Si la extracción falla o el archivo no es PDF, degrada con gracia:
    devuelve success=False con error_message, sin lanzar 4xx/5xx.
    """
    content = await file.read()

    # F3(b): rechazar archivos mayores al límite (degradación gracia, no 5xx)
    if len(content) > MAX_PDF_BYTES:
        record_audit(
            db,
            actor=current_user.username,
            action="CREATE",
            entity="pdf_extract_attempt",
            entity_id=None,
        )
        db.commit()
        return PdfExtractResult(
            success=False,
            raw_text="",
            fields=[],
            error_message=f"El archivo supera el límite de {MAX_PDF_BYTES // (1024 * 1024)} MB.",
        )

    try:
        pages = parser.extract(content)
    except ExtractionError as exc:
        record_audit(
            db,
            actor=current_user.username,
            action="CREATE",
            entity="pdf_extract_attempt",
            entity_id=None,
        )
        db.commit()
        return PdfExtractResult(
            success=False,
            raw_text="",
            fields=[],
            error_message=str(exc),
        )

    # F3(b): cap de páginas — procesar solo las primeras MAX_PDF_PAGES
    pages = pages[:MAX_PDF_PAGES]

    raw_text = "\n".join(p.text for p in pages)
    fields = _mapear_campos(raw_text)

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="pdf_extract_attempt",
        entity_id=None,
    )
    db.commit()

    return PdfExtractResult(
        success=True,
        raw_text=raw_text,
        fields=fields,
        error_message=None,
    )


@router.post(
    "/confirm",
    dependencies=[Depends(_writer)],
)
def confirm_extraction(
    payload: PdfConfirmPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """Confirma los datos editados por el administrativo.

    Valida que exista una versión publicada del formulario destino y valida
    el payload contra sus FieldDefs (CEPA-111 RN-4 / TC-112-05):
      - Campos required+active deben estar presentes y no vacíos.
      - Campos select con domain_values rechazan valores fuera del dominio.

    La persistencia real en la entidad de dominio (ingreso, etc.)
    es responsabilidad del endpoint del módulo correspondiente.

    Retorna confirmación con conteo de campos recibidos.
    """
    # Verificar que exista versión publicada del formulario destino
    published = form_svc.get_published_version(db, payload.form_key)  # lanza 404 si no existe

    # Construir mapa de field_key → valor recibido
    payload_map = {f.field_key: f.value for f in payload.fields}

    # Validar contra FieldDefs activos de la versión publicada
    missing: list[str] = []
    out_of_domain: list[str] = []
    for field_def in published.fields:
        if not field_def.active:
            continue
        value = payload_map.get(field_def.field_key, "")
        if field_def.required and not value:
            missing.append(field_def.field_key)
        if (
            field_def.field_type == "select"
            and field_def.domain_values
            and value
            and value not in field_def.domain_values
        ):
            out_of_domain.append(field_def.field_key)

    if missing or out_of_domain:
        detail: dict = {}
        if missing:
            detail["missing_required"] = missing
        if out_of_domain:
            detail["out_of_domain"] = out_of_domain
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    record_audit(
        db,
        actor=current_user.username,
        action="CREATE",
        entity="pdf_extract_confirm",
        entity_id=payload.form_key,
    )
    db.commit()

    return {
        "acknowledged": True,
        "form_key": payload.form_key,
        "received_fields": len(payload.fields),
    }
