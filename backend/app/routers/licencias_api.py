"""Router de Licencias — CEPA-121 CA-4.

Expone historial de licencias y días acumulados por folio.
Reutiliza calcular_acumulado de EPIC-07 (app.services.licencias_acumulado).
calcular_acumulado recibe ingreso_id (no folio), devuelve ResultadoAcumulado
con campo dias_acumulados_vigentes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.schemas.licencia_api import LicenciaRead, LicenciasResponse

router = APIRouter(prefix="/api/v1/licencias", tags=["licencias"])

_reader = require_role("Administrativo", "Coordinacion", "Auditor")


@router.get(
    "/folio/{folio}",
    response_model=LicenciasResponse,
    dependencies=[Depends(_reader)],
)
def obtener_licencias(folio: str, db: Session = Depends(get_db)) -> LicenciasResponse:
    """CA-4: historial de licencias y días acumulados del folio.

    Usa calcular_acumulado de EPIC-07 con ingreso_id. Si el folio no existe → 404.
    """
    from app.models.ingreso import Ingreso

    ingreso = db.execute(
        select(Ingreso).where(Ingreso.folio == folio)
    ).scalar_one_or_none()
    if ingreso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe ingreso con folio {folio!r}",
        )

    try:
        from app.models.licencia import LicenciaMedica
        from app.services.licencias_acumulado import calcular_acumulado
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Módulo de Licencias (EPIC-07) aún no disponible en este entorno.",
        )

    licencias = list(
        db.scalars(
            select(LicenciaMedica).where(LicenciaMedica.ingreso_id == ingreso.id)
        ).all()
    )
    # calcular_acumulado toma ingreso_id y devuelve ResultadoAcumulado
    resultado = calcular_acumulado(db, ingreso.id)
    return LicenciasResponse(
        folio=folio,
        historial=[LicenciaRead.model_validate(lic) for lic in licencias],
        dias_acumulados=resultado.dias_acumulados_vigentes,
    )
