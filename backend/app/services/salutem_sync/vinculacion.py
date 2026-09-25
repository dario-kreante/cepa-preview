"""Paso 2 del sync: de la copia de SALUTEM a ficha_clinica. No habla con SALUTEM.

Una atención se vincula a los ingresos del paciente CEPA con el mismo RUT cuya
ventana contiene la fecha de la cita (misma regla que el pull manual). Las
atenciones de personas sin paciente CEPA quedan pendientes y se vinculan solas
cuando el paciente aparece.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.ficha_clinica import FichaClinica
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.services.salutem_sync.controles import es_control, sincronizar_control
from app.services.salutem_sync.filtro import cruce_con_paciente
from app.models.salutem_copia import SalutemAtencion, SalutemPersona
from app.services.ficha_clinica import _en_ventana_del_ingreso
from app.services.salutem_sync.tipos import a_utc

ACTOR = "sistema:salutem-sync"

log = logging.getLogger("salutem_sync")


@dataclass
class ResultadoVinculacion:
    atenciones_revisadas: int = 0
    fichas_nuevas: int = 0
    fichas_actualizadas: int = 0
    fichas_eliminadas: int = 0
    errores: list[str] = field(default_factory=list)

    def sumar(self, otro: "ResultadoVinculacion") -> None:
        self.fichas_nuevas += otro.fichas_nuevas
        self.fichas_actualizadas += otro.fichas_actualizadas
        self.fichas_eliminadas += otro.fichas_eliminadas


def vincular(
    db: Session,
    ahora: datetime,
    *,
    todo: bool = False,
    ingresos_desde: datetime | None = None,
    lote: int = 200,
    al_avanzar: Callable[[], None] = lambda: None,
) -> ResultadoVinculacion:
    """Aplica a ficha_clinica las atenciones pendientes.

    `todo=True` revisa todas las atenciones con paciente CEPA (modo fría y backfill).
    `ingresos_desde` agrega las atenciones de pacientes con ingresos creados o
    editados desde ese momento, que pueden haber ganado atenciones antiguas.

    Cada atención va en su propio savepoint: si una falla queda pendiente (se reintenta
    en la próxima corrida) y el error se informa, sin bloquear a las demás.
    `al_avanzar` se llama en cada lote confirmado (el orquestador renueva el lease).
    """
    ahora = a_utc(ahora)
    resultado = ResultadoVinculacion()
    consulta = (
        select(SalutemAtencion.cita_id, Paciente.id)
        .join(SalutemPersona, SalutemPersona.salutem_id == SalutemAtencion.persona_id)
        .join(Paciente, cruce_con_paciente())
        .order_by(SalutemAtencion.cita_id)
    )
    if not todo:
        condicion = or_(
            SalutemAtencion.hash_vinculado.is_(None),
            SalutemAtencion.hash_vinculado != SalutemAtencion.hash_contenido,
        )
        if ingresos_desde is not None:
            condicion = or_(
                condicion,
                Paciente.id.in_(
                    select(Ingreso.paciente_id).where(Ingreso.updated_at >= ingresos_desde)
                ),
            )
        consulta = consulta.where(condicion)

    for n, (cita_id, paciente_id) in enumerate(db.execute(consulta).all(), start=1):
        # Contadores aparte: si el savepoint se revierte, lo contado tampoco ocurrió.
        parcial = ResultadoVinculacion()
        try:
            with db.begin_nested():
                atencion = db.get(SalutemAtencion, cita_id)
                # Consulta explícita y no `paciente.ingresos`: con expire_on_commit=False la
                # colección cargada en una vinculación anterior no vería un ingreso nuevo.
                ingresos = db.scalars(select(Ingreso).where(Ingreso.paciente_id == paciente_id)).all()
                for ingreso in ingresos:
                    if _en_ventana_del_ingreso(atencion.fecha_cita, ingreso):
                        _aplicar(db, atencion, ingreso, ahora, parcial)
                        if es_control(atencion):
                            sincronizar_control(db, atencion, ingreso)
                atencion.hash_vinculado = atencion.hash_contenido
            resultado.sumar(parcial)
        except Exception as e:  # noqa: BLE001 — una atención mala no debe frenar al resto
            log.warning("Vinculación de la cita %s falló: %s: %s", cita_id, type(e).__name__, e)
            resultado.errores.append(f"cita {cita_id}: {type(e).__name__}: {e}")
        resultado.atenciones_revisadas += 1
        if n % lote == 0:
            db.commit()
            al_avanzar()
    db.commit()
    return resultado


def _aplicar(
    db: Session,
    atencion: SalutemAtencion,
    ingreso: Ingreso,
    ahora: datetime,
    resultado: ResultadoVinculacion,
) -> None:
    ficha = db.scalars(
        select(FichaClinica)
        .where(
            FichaClinica.ingreso_id == ingreso.id,
            FichaClinica.salutem_cita_id == atencion.cita_id,
        )
        .order_by(FichaClinica.id)
    ).first()

    if atencion.desaparecida_en is not None:
        if ficha is not None and ficha.eliminada_en_origen is None:
            ficha.eliminada_en_origen = ahora
            db.flush()
            _auditar(db, "UPDATE", ficha)
            resultado.fichas_eliminadas += 1
        return

    if ficha is None:
        ficha = FichaClinica(
            ingreso_id=ingreso.id,
            folio=ingreso.folio,
            origen="SALUTEM",
            contenido=atencion.contenido,
            salutem_cita_id=atencion.cita_id,
        )
        db.add(ficha)
        db.flush()
        _auditar(db, "CREATE", ficha)
        resultado.fichas_nuevas += 1
        return

    if ficha.contenido != atencion.contenido or ficha.eliminada_en_origen is not None:
        ficha.contenido = atencion.contenido
        ficha.eliminada_en_origen = None
        db.flush()
        _auditar(db, "UPDATE", ficha)
        resultado.fichas_actualizadas += 1


def _auditar(db: Session, accion: str, ficha: FichaClinica) -> None:
    record_audit(db, actor=ACTOR, action=accion, entity="ficha_clinica", entity_id=str(ficha.id))
