"""Corrida completa del job de alertas — COMP-2609-06.

Junta en una sola ejecución lo que antes solo se disparaba con botones:
  1. el motor de plazos perentorios (``ejecutar_job_alertas`` → ``alerta_notif``);
  2. las alertas de vencimiento de licencias (``alerta_licencia``, CEPA-072);
  3. las alertas de revisión de recetas (``alerta``, CEPA-022).

Cada paso es idempotente por diseño, así que correrlo dos veces el mismo día no duplica.
La auditoría queda con ``actor = sistema``. Lo invoca ``app.scripts.alertas_job`` (cron).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.services.alertas import ejecutar_job_alertas
from app.services.farmacos import generar_alertas_revision
from app.services.licencias_alerta import generar_alertas_vencimiento

ACTOR_SISTEMA = "sistema"


def correr_job_alertas(
    db: Session, *, hoy: date | None = None, actor: str = ACTOR_SISTEMA
) -> dict[str, int]:
    """Ejecuta los tres generadores y devuelve cuántas alertas nuevas creó cada uno."""
    motor = ejecutar_job_alertas(db, actor=actor, hoy=hoy)

    licencias = generar_alertas_vencimiento(db, hoy=hoy)
    if licencias:
        record_audit(
            db, actor=actor, action="CREATE",
            entity="alerta_licencia", entity_id=f"batch:{len(licencias)}",
        )
    db.commit()

    recetas = generar_alertas_revision(db, hoy=hoy)
    for alerta in recetas:
        record_audit(db, actor=actor, action="CREATE", entity="alerta", entity_id=str(alerta.id))
    db.commit()

    return {"motor": motor, "licencias": len(licencias), "recetas": len(recetas)}
