"""Router de lectura de documentos PDF (CEPA-112 P1).

El parser se inyecta vía dependencia FastAPI: en producción usa PypdfParser;
en tests se puede sobreescribir con un stub.

Degradación gracia (RN-3): si la extracción falla, devuelve success=False
con error_message y fields=[], sin bloquear el flujo de captura manual.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.pdf_extract import ExtractedFieldOut, PdfConfirmPayload, PdfExtractResult
from app.services.pdf_parser import ExtractionError, PdfParser, PypdfParser
from app.services import form_config as form_svc

router = APIRouter(prefix="/api/v1/pdf-extract", tags=["pdf-extract"])

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

    Valida que exista una versión publicada del formulario destino.
    La persistencia real en la entidad de dominio (ingreso, etc.)
    es responsabilidad del endpoint del módulo correspondiente.

    Retorna confirmación con conteo de campos recibidos.
    """
    # Verificar que exista versión publicada del formulario destino
    form_svc.get_published_version(db, payload.form_key)  # lanza 404 si no existe

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
