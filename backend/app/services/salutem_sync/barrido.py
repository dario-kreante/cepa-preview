"""Barrido de SALUTEM hacia la copia local: un día a la vez (solo lectura, D12)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.errors import (
    SalutemAuthError,
    SalutemError,
    SalutemUnavailableError,
)
from app.integrations.salutem.models import EstadoCitaSalutem, TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.services.salutem_sync import copia
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores, Resultado

# Hipótesis a validar en QA (Task 15): solo las citas atendidas tienen ficha clínica.
ESTADOS_CON_ATENCION = frozenset({int(EstadoCitaSalutem.ATENDIDO)})

# Orden de ciclo de vida, no numérico: una cita avanza AGENDADO → ... → ATENDIDO (o
# ANULADO/NO_ASISTE). Consultar en orden de id numérico (AGENDADO=1, ANULADO=2,
# ATENDIDO=3, AGENDADO_WEB=4, CONFIRMADO=5, CONFIRMADO_WEB=6, CONFIRMADO_EMAIL=7,
# RECEPCIONADO=8, NO_ASISTE=9) deja huecos: una cita que avanza de RECEPCIONADO(8) a
# ATENDIDO(3) entre que se consulta un estado y el siguiente ya pasó por ATENDIDO sin
# encontrarla y nunca vuelve a consultarlo, así que queda sin ver en ningún estado y
# se marcaría desaparecida por error. Consultando en orden de ciclo de vida, el estado
# al que una cita avanza siempre se consulta después del que tenía, así que como mucho
# aparece dos veces (una por estado) y los duplicados los absorbe `vistas` (es un set).
ORDEN_ESTADOS = (
    EstadoCitaSalutem.AGENDADO,
    EstadoCitaSalutem.AGENDADO_WEB,
    EstadoCitaSalutem.CONFIRMADO,
    EstadoCitaSalutem.CONFIRMADO_WEB,
    EstadoCitaSalutem.CONFIRMADO_EMAIL,
    EstadoCitaSalutem.RECEPCIONADO,
    EstadoCitaSalutem.ATENDIDO,
    EstadoCitaSalutem.ANULADO,
    EstadoCitaSalutem.NO_ASISTE,
)


def es_error_de_registro(e: BaseException) -> bool:
    """True si el error afecta a un registro puntual y la corrida puede seguir.

    Una credencial rechazada o SALUTEM caído (tras los reintentos de `Ritmo`) valen
    para todo lo que queda: esos abortan la corrida. Cualquier otro rechazo
    (petición inválida, código no catalogado) se registra y se salta ese registro.
    """
    return isinstance(e, SalutemError) and not isinstance(
        e, (SalutemAuthError, SalutemUnavailableError)
    )


def describir_error(e: SalutemError) -> str:
    """Código de SALUTEM, o tipo y mensaje cuando no hay código (p.ej. un HTTP 504)."""
    return e.codigo or f"{type(e).__name__}: {e}"


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

    for estado in ORDEN_ESTADOS:
        try:
            citas = ritmo.llamar(cliente.listar_citas, fecha, estado, tipo)
        except SalutemError as e:
            if not es_error_de_registro(e):
                raise
            resultado.completo = False
            resultado.errores.append(f"{fecha.isoformat()} estado {int(estado)}: {describir_error(e)}")
            continue
        for cita in citas:
            vistas.add(cita.cita_id)
            guardado = copia.guardar_cita(db, cita, ahora)
            resultado.contadores.registrar(guardado)
            try:
                asegurar_persona(db, cliente, ritmo, cita.persona_id, ahora, resultado.contadores)
                if cita.estado_id in ESTADOS_CON_ATENCION and (
                    guardado is not Resultado.IGUAL or not _atencion_existe(db, cita.cita_id)
                ):
                    traer_atencion(
                        db, cliente, ritmo, cita.persona_id, cita.cita_id, ahora, resultado.contadores
                    )
            except SalutemError as e:
                if not es_error_de_registro(e):
                    raise
                # Un día con un registro sin traer no está completo: no se marcan
                # desaparecidas y el backfill no lo registra, así que se reintenta.
                resultado.completo = False
                resultado.errores.append(f"cita {cita.cita_id}: {describir_error(e)}")

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
    existe = db.scalar(
        select(SalutemPersona.salutem_id).where(SalutemPersona.salutem_id == persona_id)
    )
    if existe is not None:
        return
    persona = ritmo.llamar(cliente.obtener_persona, persona_id)
    if persona is not None:
        contadores.registrar(copia.guardar_persona(db, persona, ahora))


def _atencion_existe(db: Session, cita_id: int) -> bool:
    """Como `db.get(SalutemAtencion, cita_id) is None` pero sin cargar el CLOB de contenido."""
    return db.scalar(select(SalutemAtencion.cita_id).where(SalutemAtencion.cita_id == cita_id)) is not None


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
    al_avanzar: Callable[[], None] = lambda: None,
    errores: list[str] | None = None,
) -> Contadores:
    """Vuelve a traer las atenciones de un rango de fechas para detectar ediciones.

    `al_avanzar` se llama en cada lote confirmado: en la fría son cientos de llamadas
    y el orquestador lo usa para renovar el lease. Las atenciones que SALUTEM rechaza
    se saltan y se anotan en `errores` (si se pasa).
    """
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
        try:
            traer_atencion(db, cliente, ritmo, persona_id, cita_id, ahora, contadores)
        except SalutemError as e:
            if not es_error_de_registro(e):
                raise
            if errores is not None:
                errores.append(f"cita {cita_id}: {describir_error(e)}")
        if i % lote == 0:
            db.commit()
            al_avanzar()
    db.commit()
    return contadores
