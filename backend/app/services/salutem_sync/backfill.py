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
from app.services.salutem_sync.barrido import ResultadoDia, barrer_dia, traer_atencion
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores, Resultado

DIAS_FUTURO = 180
_UN_DIA = timedelta(days=1)


@dataclass
class ResultadoBackfill:
    dias_barridos: int = 0
    dias_con_error: int = 0
    primer_dia_con_datos: date | None = None
    atenciones_recuperadas: int = 0
    # Recuperadas con fecha anterior al primer día con citas: sugiere re-ejecutar con --desde.
    atenciones_anteriores: int = 0
    contadores: Contadores = field(default_factory=Contadores)
    errores: list[str] = field(default_factory=list)

    def sumar_dia(self, dia: ResultadoDia) -> None:
        self.dias_barridos += 1
        self.contadores.sumar(dia.contadores)
        if not dia.completo:
            self.dias_con_error += 1
            self.errores.extend(dia.errores)


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
        resultado.sumar_dia(barrer_dia(db, cliente, ritmo, hoy + i * _UN_DIA, tipo, ahora))
        al_terminar_dia()

    dia = hoy
    vacios = 0
    while True:
        if desde is not None and dia < desde:
            break
        if desde is None and vacios >= dias_vacios_para_parar:
            break
        registrado = db.get(SalutemSyncDia, (dia, int(tipo))) if dia < hoy else None
        if registrado is not None:
            citas = registrado.citas
        else:
            barrido = barrer_dia(db, cliente, ritmo, dia, tipo, ahora)
            resultado.sumar_dia(barrido)
            citas = barrido.citas
            # Hoy no se registra: sigue cambiando. Un día con errores tampoco: se reintenta.
            if barrido.completo and dia < hoy:
                db.add(SalutemSyncDia(fecha=dia, tipo=int(tipo), citas=citas, completado_en=ahora))
                db.commit()
            al_terminar_dia()
        if citas > 0:
            vacios = 0
            resultado.primer_dia_con_datos = dia
        else:
            vacios += 1
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
    limite = resultado.primer_dia_con_datos
    for n, persona_id in enumerate(personas, start=1):
        for cita in ritmo.llamar(cliente.listar_atenciones, persona_id):
            if db.get(SalutemAtencion, cita.cita_id) is not None:
                continue
            guardado = traer_atencion(
                db, cliente, ritmo, persona_id, cita.cita_id, ahora, resultado.contadores
            )
            if guardado is Resultado.NUEVO:
                resultado.atenciones_recuperadas += 1
                if limite is not None and cita.fecha is not None and cita.fecha < limite:
                    resultado.atenciones_anteriores += 1
        if n % lote == 0:
            db.commit()
            al_terminar_dia()
    db.commit()
