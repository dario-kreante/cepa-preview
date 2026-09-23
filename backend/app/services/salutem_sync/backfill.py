"""Carga inicial: todo SALUTEM desde el primer día con datos (solo lectura, D12).

1. Barre el futuro (agendas ya creadas).
2. Barre hacia atrás desde hoy, día por día, saltando los días ya registrados.
   Se detiene en `desde` o tras `dias_vacios_para_parar` días seguidos sin citas.
3. Verifica completitud persona por persona con el listado de atenciones.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.models import TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.models.salutem_sync import SalutemSyncDia
from app.integrations.salutem.errors import SalutemError, SalutemUnavailableError
from app.services.salutem_sync.barrido import (
    ResultadoDia,
    barrer_dia,
    describir_error,
    es_error_de_registro,
    traer_atencion,
)
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores, Resultado

DIAS_FUTURO = 180
_UN_DIA = timedelta(days=1)
# Días seguidos que fallan por completo (sin completar y sin citas) antes de abortar.
# Sin este tope, un rango de fechas que SALUTEM rechaza (p.ej. muy antiguo) se
# confundiría con días vacíos y el backfill gastaría miles de llamadas en vano.
DIAS_FALLIDOS_PARA_ABORTAR = 7


class BackfillAbortadoError(RuntimeError):
    """El backfill abortó tras varios días seguidos que fallaron por completo."""


@dataclass
class ResultadoBackfill:
    dias_barridos: int = 0
    dias_con_error: int = 0
    primer_dia_con_datos: date | None = None
    # Día más antiguo recorrido hacia atrás (barrido o ya registrado).
    primer_dia_barrido: date | None = None
    atenciones_recuperadas: int = 0
    # Recuperadas con fecha anterior al primer día barrido: sugiere re-ejecutar con --desde.
    atenciones_anteriores: int = 0
    contadores: Contadores = field(default_factory=Contadores)
    errores: list[str] = field(default_factory=list)

    def sumar_dia(self, dia: ResultadoDia) -> None:
        self.dias_barridos += 1
        self.contadores.sumar(dia.contadores)
        if not dia.completo:
            self.dias_con_error += 1
            self.errores.extend(dia.errores)


def _barrer_dia_tolerante(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    dia: date,
    tipo: TipoFechaCita,
    ahora: datetime,
) -> ResultadoDia:
    """Barre un día tratando una caída de SALUTEM como día fallido, no como fin de la corrida.

    El backfill dura horas: que un HTTP 504 pasajero (visto en la VM el 2026-09-17,
    tras 38.420 llamadas) tire la corrida entera obliga a relanzarla a mano. El día
    queda sin registrar y se reintenta en la próxima pasada; si SALUTEM sigue caído,
    el contador de días fallidos seguidos aborta igual, sin insistir miles de veces.
    """
    try:
        return barrer_dia(db, cliente, ritmo, dia, tipo, ahora)
    except SalutemUnavailableError as e:
        db.rollback()
        return ResultadoDia(
            fecha=dia, tipo=tipo, completo=False, errores=[f"{dia.isoformat()}: {e}"]
        )


def ejecutar_backfill(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    *,
    hoy: date,
    ahora: datetime,
    desde: date | None = None,
    dias_vacios_para_parar: int = 365,
    dias_futuro: int = DIAS_FUTURO,
    verificar: bool = True,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoBackfill:
    resultado = ResultadoBackfill()
    tipo = TipoFechaCita.FECHA_CITA

    for i in range(1, dias_futuro + 1):
        resultado.sumar_dia(
            _barrer_dia_tolerante(db, cliente, ritmo, hoy + i * _UN_DIA, tipo, ahora)
        )
        al_terminar_dia()

    dia = hoy
    vacios = 0
    fallidos_seguidos = 0
    while True:
        if desde is not None and dia < desde:
            break
        if desde is None and vacios >= dias_vacios_para_parar:
            break
        registrado = db.get(SalutemSyncDia, (dia, int(tipo))) if dia < hoy else None
        if registrado is not None:
            citas = registrado.citas
            completo = True  # Un día registrado es completo por definición.
        else:
            barrido = _barrer_dia_tolerante(db, cliente, ritmo, dia, tipo, ahora)
            resultado.sumar_dia(barrido)
            citas = barrido.citas
            completo = barrido.completo
            # Hoy no se registra: sigue cambiando. Un día con errores tampoco: se reintenta.
            if barrido.completo and dia < hoy:
                db.add(SalutemSyncDia(fecha=dia, tipo=int(tipo), citas=citas, completado_en=ahora))
                db.commit()
            al_terminar_dia()
        if not completo and citas == 0:
            # Un día que falló entero no es un día vacío: no sabemos si tenía citas.
            # Contarlo como vacío haría que un rango rechazado por SALUTEM (p.ej. muy
            # antiguo) se confundiera con "no hay más datos" y gastara miles de
            # llamadas antes de pararse. En cambio, si fallan demasiados seguidos,
            # se aborta explícitamente.
            fallidos_seguidos += 1
            if fallidos_seguidos >= DIAS_FALLIDOS_PARA_ABORTAR:
                raise BackfillAbortadoError(
                    f"backfill abortado: {fallidos_seguidos} días fallidos seguidos "
                    f"hasta {dia.isoformat()}; últimos errores: "
                    f"{resultado.errores[-fallidos_seguidos:]}"
                )
        else:
            fallidos_seguidos = 0
            if citas > 0:
                vacios = 0
                resultado.primer_dia_con_datos = dia
            else:
                vacios += 1
        resultado.primer_dia_barrido = dia
        dia -= _UN_DIA

    if verificar:
        _verificar_completitud(db, cliente, ritmo, resultado, ahora, al_terminar_dia)
    return resultado


def _verificar_completitud(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    resultado: ResultadoBackfill,
    ahora: datetime,
    al_terminar_dia: Callable[[], None],
    lote: int = 50,
) -> None:
    """Pide la historia de cada persona y trae las atenciones que la copia no tiene."""
    personas = db.scalars(select(SalutemPersona.salutem_id).order_by(SalutemPersona.salutem_id)).all()
    # Se compara contra el rango recorrido y no contra el primer día con citas: si el
    # rango no tenía ninguna (visto en QA), igual hay que avisar de la historia anterior.
    limite = resultado.primer_dia_barrido
    for n, persona_id in enumerate(personas, start=1):
        # Una sola consulta por persona (sin cargar el CLOB de contenido) en vez de un
        # `db.get` por cada cita: `copia` hace flush tras cada `add`, así que el select
        # ve también las atenciones agregadas en esta misma transacción.
        ya = set(
            db.scalars(
                select(SalutemAtencion.cita_id).where(SalutemAtencion.persona_id == persona_id)
            )
        )
        try:
            listadas = ritmo.llamar(cliente.listar_atenciones, persona_id)
        except SalutemError as e:
            # Una caída pasajera no debe tirar la verificación de miles de personas:
            # se anota y se sigue con la siguiente.
            if not (es_error_de_registro(e) or isinstance(e, SalutemUnavailableError)):
                raise
            resultado.errores.append(f"persona {persona_id}: {describir_error(e)}")
            listadas = []
        for cita in listadas:
            if cita.cita_id in ya:
                continue
            try:
                guardado = traer_atencion(
                    db, cliente, ritmo, persona_id, cita.cita_id, ahora, resultado.contadores
                )
            except SalutemError as e:
                if not es_error_de_registro(e):
                    raise
                resultado.errores.append(f"cita {cita.cita_id}: {describir_error(e)}")
                continue
            if guardado is Resultado.NUEVO:
                resultado.atenciones_recuperadas += 1
                if limite is not None and cita.fecha is not None and cita.fecha < limite:
                    resultado.atenciones_anteriores += 1
        if n % lote == 0:
            db.commit()
            al_terminar_dia()
    db.commit()
