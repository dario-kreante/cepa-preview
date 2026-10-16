"""Lista de pacientes borrador pendientes de folio y su descarte."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums import EstadoRegistroPaciente
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.schemas.paciente_borrador import PacientePendienteRead
from app.services.salutem_sync.borradores import resolver_alerta_borrador

MAX_ESPECIALIDADES = 5


def listar_pendientes(db: Session) -> list[PacientePendienteRead]:
    pacientes = list(
        db.scalars(
            select(Paciente)
            .where(Paciente.estado_registro == EstadoRegistroPaciente.PENDIENTE_FOLIO.value)
            .order_by(Paciente.created_at, Paciente.id)
        )
    )
    persona_ids = [p.salutem_persona_id for p in pacientes if p.salutem_persona_id is not None]
    identificaciones: dict[int, str | None] = {}
    atenciones: dict[int, list[SalutemAtencion]] = {}
    if persona_ids:
        for persona in db.scalars(select(SalutemPersona).where(SalutemPersona.salutem_id.in_(persona_ids))):
            valor = persona.contenido.get("identificacion")
            identificaciones[persona.salutem_id] = str(valor) if valor else None
        for a in db.scalars(
            select(SalutemAtencion)
            .where(SalutemAtencion.persona_id.in_(persona_ids), SalutemAtencion.desaparecida_en.is_(None))
            .order_by(SalutemAtencion.fecha_cita, SalutemAtencion.cita_id)
        ):
            atenciones.setdefault(a.persona_id, []).append(a)

    filas = []
    for p in pacientes:
        propias = atenciones.get(p.salutem_persona_id, []) if p.salutem_persona_id is not None else []
        fechas = [a.fecha_cita for a in propias if a.fecha_cita is not None]
        especialidades: list[str] = []
        for a in propias:
            esp = a.contenido.get("especialidadNombre")
            if esp and esp not in especialidades:
                especialidades.append(str(esp))
        filas.append(
            PacientePendienteRead(
                id=p.id,
                nombre=p.nombre,
                rut=p.rut,
                identificacion_salutem=identificaciones.get(p.salutem_persona_id),
                salutem_persona_id=p.salutem_persona_id,
                creado_en=p.created_at,
                primera_atencion=min(fechas) if fechas else None,
                ultima_atencion=max(fechas) if fechas else None,
                atenciones=len(propias),
                especialidades=especialidades[:MAX_ESPECIALIDADES],
            )
        )
    return filas


def descartar(db: Session, paciente_id: int, motivo: str, actor: str) -> Paciente:
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    if paciente.estado_registro != EstadoRegistroPaciente.PENDIENTE_FOLIO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden descartar pacientes pendientes de folio",
        )
    paciente.estado_registro = EstadoRegistroPaciente.DESCARTADO.value
    paciente.motivo_descarte = motivo
    paciente.descartado_por = actor
    paciente.descartado_en = datetime.now(timezone.utc)
    db.flush()
    resolver_alerta_borrador(db, paciente.id)
    record_audit(db, actor=actor, action="UPDATE", entity="paciente", entity_id=str(paciente.id))
    db.commit()
    db.refresh(paciente)
    return paciente
