"""Barrido de SALUTEM hacia la copia local: un día a la vez (solo lectura, D12)."""

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.errors import SalutemRequestError
from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.services.salutem_sync import copia
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores, Resultado

# Hipótesis a validar en QA (Task 15): solo las citas atendidas tienen ficha clínica.
ESTADOS_CON_ATENCION = frozenset({int(EstadoCitaSalutem.ATENDIDO)})


@dataclass
class ResultadoDia:
    fecha: date
    tipo: TipoFechaCita
    citas: int = 0
    completo: bool = True
    contadores: Contadores = field(default_factory=Contadores)
    errores: list[str] = field(default_factory=list)


def barrer_dia(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    fecha: date,
    tipo: TipoFechaCita,
    ahora: datetime,
) -> ResultadoDia:
    """Trae las citas de un día (9 estados), sus personas nuevas y sus atenciones.

    Confirma todo el día en una sola transacción: si el proceso muere a la
    mitad, el día se repite entero y el resultado es el mismo.
    """
    resultado = ResultadoDia(fecha=fecha, tipo=tipo)
    vistas: set[int] = set()

    for estado in EstadoCitaSalutem:
        try:
            citas = ritmo.llamar(cliente.listar_citas, fecha, estado, tipo)
        except SalutemRequestError as e:
            resultado.completo = False
            resultado.errores.append(f"{fecha.isoformat()} estado {int(estado)}: {e.codigo}")
            continue
        for cita in citas:
            vistas.add(cita.cita_id)
            guardado = copia.guardar_cita(db, cita, ahora)
            resultado.contadores.registrar(guardado)
            asegurar_persona(db, cliente, ritmo, cita.persona_id, ahora, resultado.contadores)
            if cita.estado_id in ESTADOS_CON_ATENCION and (
                guardado is not Resultado.IGUAL or db.get(SalutemAtencion, cita.cita_id) is None
            ):
                traer_atencion(
                    db, cliente, ritmo, cita.persona_id, cita.cita_id, ahora, resultado.contadores
                )

    resultado.citas = len(vistas)
    # Solo por fecha de cita y con los 9 estados respondidos se puede afirmar que
    # una cita ya no existe: por fecha de creación una cita puede cambiar de día.
    if tipo == TipoFechaCita.FECHA_CITA and resultado.completo:
        resultado.contadores.desaparecidos += copia.marcar_citas_desaparecidas(
            db, fecha, vistas, ahora
        )
    db.commit()
    return resultado


def asegurar_persona(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    persona_id: int,
    ahora: datetime,
    contadores: Contadores,
) -> None:
    if db.get(SalutemPersona, persona_id) is not None:
        return
    persona = ritmo.llamar(cliente.obtener_persona, persona_id)
    if persona is not None:
        contadores.registrar(copia.guardar_persona(db, persona, ahora))


def traer_atencion(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    persona_id: int,
    cita_id: int,
    ahora: datetime,
    contadores: Contadores,
) -> Resultado | None:
    """Trae una atención a la copia. None si SALUTEM ya no la tiene (queda marcada)."""
    atencion = ritmo.llamar(cliente.obtener_atencion, persona_id, cita_id)
    if atencion is None:
        if copia.marcar_atencion_desaparecida(db, cita_id, ahora):
            contadores.desaparecidos += 1
        return None
    guardado = copia.guardar_atencion(db, atencion, ahora)
    contadores.registrar(guardado)
    return guardado


def refrescar_atenciones(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    desde: date,
    hasta: date,
    ahora: datetime,
    lote: int = 50,
) -> Contadores:
    """Vuelve a traer las atenciones de un rango de fechas para detectar ediciones."""
    contadores = Contadores()
    claves = db.execute(
        select(SalutemAtencion.persona_id, SalutemAtencion.cita_id)
        .where(
            SalutemAtencion.fecha_cita >= desde,
            SalutemAtencion.fecha_cita <= hasta,
            SalutemAtencion.desaparecida_en.is_(None),
        )
        .order_by(SalutemAtencion.cita_id)
    ).all()
    for i, (persona_id, cita_id) in enumerate(claves, start=1):
        traer_atencion(db, cliente, ritmo, persona_id, cita_id, ahora, contadores)
        if i % lote == 0:
            db.commit()
    db.commit()
    return contadores
