"""Endpoint de salud bajo /api/v2 — punto de anclaje del enrutador v2.

v2 introduce cambios de contrato incompatibles con v1 sin romper v1.
Actualmente solo expone /health como demostrador de coexistencia.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v2", tags=["v2"])


@router.get("/health")
def health_v2() -> dict[str, str]:
    """Salud de la API v2 (TC-120-06)."""
    return {"status": "ok", "version": "v2"}
