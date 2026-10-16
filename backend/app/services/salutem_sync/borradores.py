"""Pacientes borrador: personas atendidas en SALUTEM que todavía no existen en el SIGE.

Corre al final de cada ciclo del sync, después de la vinculación. Cada persona con una
atención Atendida desde la fecha de corte y sin paciente (por RUT o por id de SALUTEM, en
cualquier estado de registro) recibe un paciente `pendiente_folio` y una alerta sin
profesional asignado. Idempotente: con paciente, la persona nunca vuelve a ser candidata.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums import EstadoRegistroPaciente, OrigenPaciente
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.integrations.salutem.models import EstadoCitaSalutem
from app.models.alertas import AlertaNotif
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.services.config_alertas import cargar_ventanas
from app.services.salutem_sync.alertas_control import ACTOR
from app.services.salutem_sync.filtro import cruce_con_paciente
from app.services.salutem_sync.incremental import hoy_en_santiago

CASO_TIPO = "paciente"
_TIPO = TipoAlerta.PACIENTE_PENDIENTE_FOLIO.value
_SEXOS = {"hombre": "M", "mujer": "F"}


@dataclass
class ResultadoBorradores:
    creados: int = 0
    errores: list[str] = field(default_factory=list)


def _texto(valor: Any, maximo: int) -> str | None:
    if valor is None:
        return None
    limpio = str(valor).strip()
    return limpio[:maximo] or None


def _sexo(valor: Any) -> str | None:
    texto = _texto(valor, 40)
    if texto is None:
        return None
    return _SEXOS.get(texto.casefold(), "otro")


def _edad(valor: Any, hoy: date) -> int | None:
    try:
        nacimiento = datetime.strptime(str(valor).strip(), "%d-%m-%Y").date()
    except (TypeError, ValueError):
        return None
    edad = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    return edad if edad >= 0 else None


def paciente_desde_persona(persona: SalutemPersona, hoy: date) -> Paciente:
    """Paciente borrador con los datos de SALUTEM (sin persistir)."""
    c = persona.contenido
    nombre = " ".join(
        x for x in (_texto(c.get("nombres"), 160), _texto(c.get("apellidos"), 160)) if x
    )
    nombre = nombre or _texto(c.get("identificacion"), 160) or f"Persona SALUTEM {persona.salutem_id}"
    return Paciente(
        nombre=nombre[:160],
        rut=persona.rut,
        sexo=_sexo(c.get("sexo")),
        edad=_edad(c.get("fechaNacimiento"), hoy),
        region=None,
        comuna=_texto(c.get("comuna"), 80),
        telefono=_texto(c.get("telefonoMovil"), 30),
        correo=_texto(c.get("email"), 120),
        salutem_persona_id=persona.salutem_id,
        estado_registro=EstadoRegistroPaciente.PENDIENTE_FOLIO.value,
        origen=OrigenPaciente.SALUTEM.value,
    )


def _es_atendida(contenido: dict[str, Any]) -> bool:
    try:
        return int(contenido.get("estadoCitaId")) == int(EstadoCitaSalutem.ATENDIDO)
    except (TypeError, ValueError):
        return False


def _candidatas(db: Session, desde: date) -> list[SalutemPersona]:
    """Personas con atenciones desde el corte y sin paciente; atendidas, filtradas en Python."""
    sin_paciente = ~exists().where(cruce_con_paciente())
    # Una sola consulta con join (sin listas IN literales: Oracle admite máximo 1000 elementos).
    personas: dict[int, SalutemPersona] = {}
    atendidas: set[int] = set()
    filas = db.execute(
        select(SalutemPersona, SalutemAtencion.contenido)
        .join(SalutemAtencion, SalutemAtencion.persona_id == SalutemPersona.salutem_id)
        .where(
            sin_paciente,
            SalutemAtencion.desaparecida_en.is_(None),
            SalutemAtencion.fecha_cita >= desde,
        )
        .order_by(SalutemPersona.salutem_id)
    )
    for persona, contenido in filas:
        personas.setdefault(persona.salutem_id, persona)
        if _es_atendida(contenido):
            atendidas.add(persona.salutem_id)
    return [p for sid, p in sorted(personas.items()) if sid in atendidas]


def crear_borradores(db: Session, ahora: datetime, desde: date | None) -> ResultadoBorradores:
    resultado = ResultadoBorradores()
    if desde is None:
        return resultado
    hoy = hoy_en_santiago(ahora)
    alertar = cargar_ventanas(db).get(_TIPO, {}).get("activo", True)
    for persona in _candidatas(db, desde):
        try:
            with db.begin_nested():
                paciente = paciente_desde_persona(persona, hoy)
                db.add(paciente)
                db.flush()
                if alertar:
                    db.add(
                        AlertaNotif(
                            tipo=_TIPO,
                            estado=EstadoAlerta.PENDIENTE.value,
                            caso_id=paciente.id,
                            caso_tipo=CASO_TIPO,
                            usuario_id=None,
                            plazo_objetivo=datetime.combine(hoy, time.min, tzinfo=timezone.utc),
                            ventana_dias=0,
                            email_enviado=False,
                        )
                    )
                record_audit(db, actor=ACTOR, action="CREATE", entity="paciente", entity_id=str(paciente.id))
            resultado.creados += 1
        except Exception as e:  # noqa: BLE001 — una persona con datos raros no detiene a las demás
            resultado.errores.append(f"persona {persona.salutem_id}: {type(e).__name__}: {e}")
    return resultado


def resolver_alerta_borrador(db: Session, paciente_id: int) -> None:
    """Resuelve las alertas abiertas de un borrador (al completarlo o descartarlo)."""
    ahora = datetime.now(timezone.utc)
    for alerta in db.scalars(
        select(AlertaNotif).where(
            AlertaNotif.caso_tipo == CASO_TIPO,
            AlertaNotif.caso_id == paciente_id,
            AlertaNotif.tipo == _TIPO,
            AlertaNotif.estado != EstadoAlerta.RESUELTA.value,
        )
    ):
        alerta.estado = EstadoAlerta.RESUELTA.value
        alerta.resuelta_en = ahora
    db.flush()
