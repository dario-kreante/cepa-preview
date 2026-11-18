"""Alertas y casos cerrados (QA-011).

Un caso cerrado deja de generar alertas y las que tenía abiertas se resuelven al cerrarlo.
Las alertas cuelgan de entidades distintas (``caso_tipo``): cada una se vincula al ingreso
por su propia relación.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import EstadoCaso
from app.domain.enums_alertas import EstadoAlerta
from app.models.alertas import AlertaNotif
from app.models.cita import Cita
from app.models.control_medico import ControlMedico
from app.models.ept import CasoEpt, PlazoEpt
from app.models.farmacos import Receta, RegistroFarmacologico
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.oda import Oda

_ABIERTAS = (EstadoAlerta.PENDIENTE.value, EstadoAlerta.LEIDA.value)


def ingreso_cerrado(db: Session, ingreso_id: int | None) -> bool:
    """True si el ingreso está cerrado (no genera alertas nuevas)."""
    if ingreso_id is None:
        return False
    estado = db.scalar(select(Ingreso.estado).where(Ingreso.id == ingreso_id))
    return estado == EstadoCaso.CERRADO.value


def ids_ingresos_cerrados(db: Session) -> set[int]:
    """Ids de todos los ingresos cerrados, para filtrar de una vez a los generadores del job."""
    return set(db.scalars(select(Ingreso.id).where(Ingreso.estado == EstadoCaso.CERRADO.value)))


def resolver_alertas_de_ingreso(db: Session, ingreso_id: int) -> int:
    """Resuelve las alertas abiertas (pendiente/leída) de cualquier caso del ingreso."""
    # (caso_tipo, ids de la entidad cuyo ingreso es este): subconsultas, sin listas IN literales.
    por_tipo = {
        "ingreso": select(Ingreso.id).where(Ingreso.id == ingreso_id),
        "oda": select(Oda.id).where(Oda.ingreso_id == ingreso_id),
        "licencia": select(LicenciaMedica.id).where(LicenciaMedica.ingreso_id == ingreso_id),
        "control_medico": select(ControlMedico.id).where(ControlMedico.ingreso_id == ingreso_id),
        "caso_ept": select(CasoEpt.id).where(CasoEpt.ingreso_id == ingreso_id),
        "ept": select(PlazoEpt.id)
        .join(CasoEpt, CasoEpt.id == PlazoEpt.caso_ept_id)
        .where(CasoEpt.ingreso_id == ingreso_id),
        "receta": select(Receta.id)
        .join(RegistroFarmacologico, RegistroFarmacologico.id == Receta.registro_id)
        .where(RegistroFarmacologico.ingreso_id == ingreso_id),
        # Alertas de citas de SALUTEM (inasistencia, encuadre, fuera de ODA) y de atenciones.
        "salutem_cita": select(Cita.salutem_cita_id).where(
            Cita.ingreso_id == ingreso_id, Cita.salutem_cita_id.is_not(None)
        ),
        "salutem_atencion": select(Cita.salutem_cita_id).where(
            Cita.ingreso_id == ingreso_id, Cita.salutem_cita_id.is_not(None)
        ),
    }
    ahora = datetime.now(timezone.utc)
    resueltas = 0
    for caso_tipo, ids in por_tipo.items():
        alertas = db.scalars(
            select(AlertaNotif).where(
                AlertaNotif.caso_tipo == caso_tipo,
                AlertaNotif.caso_id.in_(ids),
                AlertaNotif.estado.in_(_ABIERTAS),
            )
        ).all()
        for alerta in alertas:
            alerta.estado = EstadoAlerta.RESUELTA.value
            alerta.resuelta_en = ahora
            resueltas += 1
    if resueltas:
        db.flush()
    return resueltas
