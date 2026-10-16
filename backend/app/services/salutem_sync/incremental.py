"""Ventanas del sync incremental (solo lectura, D12).

- caliente (cada 5 min): citas creadas hoy + citas de hoy y mañana, y re-lectura de los
  controles médicos de hoy y ayer (el médico suele completar la licencia o la receta al día
  siguiente, y la alerta no debe esperar a la tibia).
- tibia (cada hora): citas de -7..+30 días y re-lectura de atenciones de la última semana.
- fría (cada noche): citas de -90..+180 días y re-lectura de atenciones del último mes.

"Hoy" es el día en Santiago: SALUTEM trabaja en hora local.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.integrations.salutem.models import TipoFechaCita
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.services.salutem_sync.barrido import barrer_dia, refrescar_atenciones
from app.services.salutem_sync.ritmo import Ritmo
from app.services.salutem_sync.tipos import Contadores

ZONA = ZoneInfo("America/Santiago")
_UN_DIA = timedelta(days=1)

CALIENTE_CONTROLES_DIAS = 1
TIBIA_DIAS_ATRAS, TIBIA_DIAS_ADELANTE, TIBIA_ATENCIONES_DIAS = 7, 30, 7
FRIA_DIAS_ATRAS, FRIA_DIAS_ADELANTE, FRIA_ATENCIONES_DIAS = 90, 180, 30


@dataclass
class ResultadoVentana:
    contadores: Contadores = field(default_factory=Contadores)
    errores: list[str] = field(default_factory=list)


def hoy_en_santiago(ahora: datetime) -> date:
    return ahora.astimezone(ZONA).date()


def _barrer(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    dias: list[date],
    tipo: TipoFechaCita,
    ahora: datetime,
    resultado: ResultadoVentana,
    al_terminar_dia: Callable[[], None],
) -> None:
    for dia in dias:
        barrido = barrer_dia(db, cliente, ritmo, dia, tipo, ahora)
        resultado.contadores.sumar(barrido.contadores)
        resultado.errores.extend(barrido.errores)
        al_terminar_dia()


def _rango(hoy: date, atras: int, adelante: int) -> list[date]:
    return [hoy + i * _UN_DIA for i in range(-atras, adelante + 1)]


def ventana_caliente(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    ahora: datetime,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoVentana:
    resultado = ResultadoVentana()
    local = ahora.astimezone(ZONA)
    hoy = local.date()
    # En la primera hora del día también se barre la creación de ayer: lo creado en sus
    # últimos minutos aún no se barrió. Restar una hora real (sobre `ahora`, no sobre la
    # hora local, cuya aritmética es de reloj) en vez de mirar `hour < 1` cubre el salto
    # 24:00→01:00 del cambio de horario y una corrida perdida cerca de la medianoche.
    creacion = sorted({hoy_en_santiago(ahora - timedelta(hours=1)), hoy})
    _barrer(db, cliente, ritmo, creacion, TipoFechaCita.FECHA_CREACION, ahora, resultado, al_terminar_dia)
    _barrer(db, cliente, ritmo, [hoy, hoy + _UN_DIA], TipoFechaCita.FECHA_CITA, ahora, resultado, al_terminar_dia)
    # Solo controles médicos: son pocos por día y son los que disparan las alertas de
    # licencia y receta. Releer todas las atenciones queda para la tibia (cada hora).
    resultado.contadores.sumar(
        refrescar_atenciones(
            db, cliente, ritmo, hoy - CALIENTE_CONTROLES_DIAS * _UN_DIA, hoy, ahora,
            al_avanzar=al_terminar_dia, errores=resultado.errores,
            especialidades=get_settings().salutem_especialidades_control_set,
        )
    )
    return resultado


def ventana_tibia(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    ahora: datetime,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoVentana:
    resultado = ResultadoVentana()
    hoy = hoy_en_santiago(ahora)
    _barrer(
        db, cliente, ritmo, _rango(hoy, TIBIA_DIAS_ATRAS, TIBIA_DIAS_ADELANTE),
        TipoFechaCita.FECHA_CITA, ahora, resultado, al_terminar_dia,
    )
    resultado.contadores.sumar(
        refrescar_atenciones(
            db, cliente, ritmo, hoy - TIBIA_ATENCIONES_DIAS * _UN_DIA, hoy, ahora,
            al_avanzar=al_terminar_dia, errores=resultado.errores,
        )
    )
    return resultado


def ventana_fria(
    db: Session,
    cliente: SalutemClientProtocol,
    ritmo: Ritmo,
    ahora: datetime,
    al_terminar_dia: Callable[[], None] = lambda: None,
) -> ResultadoVentana:
    resultado = ResultadoVentana()
    hoy = hoy_en_santiago(ahora)
    _barrer(
        db, cliente, ritmo, _rango(hoy, FRIA_DIAS_ATRAS, FRIA_DIAS_ADELANTE),
        TipoFechaCita.FECHA_CITA, ahora, resultado, al_terminar_dia,
    )
    resultado.contadores.sumar(
        refrescar_atenciones(
            db, cliente, ritmo, hoy - FRIA_ATENCIONES_DIAS * _UN_DIA, hoy, ahora,
            al_avanzar=al_terminar_dia, errores=resultado.errores,
        )
    )
    return resultado
