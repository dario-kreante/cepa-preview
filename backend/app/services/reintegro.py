"""Lógica de negocio del módulo de Seguimiento de Reintegro (EPIC-04).

Las funciones validar_* lanzan HTTPException 422 cuando se viola una regla
de negocio, de modo que el router las puede llamar directamente y FastAPI
convertirá la excepción en una respuesta 422 JSON sin código adicional.
"""

import datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.reintegro_enums import EstadoReintegro
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro, Reca
from app.schemas.reintegro import (
    CasoReintegroCreate,
    CasoReintegroUpdate,
    CasoActivoResumen,
    CierreReintegroUpdate,
    PacienteConCasosRepetidosRead,
    RecaCreate,
    RecaUpdate,
)


# ── Validaciones puras (sin sesión) ───────────────────────────────────────

def _fmt(d: datetime.date) -> str:
    """Fecha como la lee el usuario en pantalla (dd-mm-aaaa)."""
    return d.strftime("%d-%m-%Y")


def validar_coherencia_reca(
    solicita_medidas: bool,
    detalle_medidas: str | None,
    fecha_medidas: datetime.date | None,
    verifica_medidas: bool = False,
    fecha_verificacion: datetime.date | None = None,
) -> None:
    """RN-2 y RN-4 CEPA-041.

    - RN-2: si solicita_medidas=True, detalle y fecha son obligatorios.
    - RN-4: si verifica_medidas=True, fecha_verificacion es obligatoria.
    """
    if solicita_medidas:
        if not detalle_medidas:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Si solicita medidas correctivas, describe cuáles son.",
            )
        if fecha_medidas is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Si solicita medidas correctivas, indica la fecha de las medidas.",
            )
    if verifica_medidas and fecha_verificacion is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Si verifica las medidas, indica la fecha de verificación.",
        )


def validar_coherencia_medidas(
    fecha_reca: datetime.date,
    fecha_medidas: datetime.date | None,
    fecha_verificacion: datetime.date | None,
) -> None:
    """RN-3 CEPA-041: fecha_verificacion >= fecha_medidas >= fecha_reca."""
    if fecha_medidas is not None and fecha_medidas < fecha_reca:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"La fecha de las medidas ({_fmt(fecha_medidas)}) no puede ser anterior "
                f"a la fecha de la RECA ({_fmt(fecha_reca)})."
            ),
        )
    if fecha_verificacion is not None and fecha_medidas is not None:
        if fecha_verificacion < fecha_medidas:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"La fecha de verificación ({_fmt(fecha_verificacion)}) no puede ser "
                    f"anterior a la fecha de las medidas ({_fmt(fecha_medidas)})."
                ),
            )


def validar_coherencia_cierre(
    estado: EstadoReintegro,
    fecha_reintegro: datetime.date | None,
    fecha_reca: datetime.date | None,
    alta_medica: bool,
    alta_psicologica: bool,
    tipo_alta: str | None,
    fecha_caso: datetime.date | None = None,
    fecha_alta_medica: datetime.date | None = None,
    fecha_alta_psico: datetime.date | None = None,
) -> None:
    """Valida las reglas de negocio del cierre del caso (CEPA-042 RN-1..4, QA-003).

    - RN-1: estado=total exige fecha_reintegro.
    - RN-2: fecha_reintegro >= fecha_reca (cuando fecha_reca disponible)
            Y fecha_reintegro >= fecha_caso (cuando fecha_caso disponible).
    - RN-4 (QA-003): reintegro total requiere al menos una de: alta médica, alta
      psicológica o un tipo de alta (el tipo de alta es opcional si hay casilla).
    - QA-003: cada casilla de alta marcada exige su fecha (en cualquier estado).

    `tipo_alta` acepta también los valores antiguos «medica» y «psicologica»: los casos
    ya guardados con ellos no deben romperse al editarse.
    """
    if alta_medica and fecha_alta_medica is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Si marcas el alta médica, indica la fecha del alta médica.",
        )
    if alta_psicologica and fecha_alta_psico is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Si marcas el alta psicológica, indica la fecha del alta psicológica.",
        )
    if estado == EstadoReintegro.TOTAL:
        if fecha_reintegro is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para un reintegro total, indica la fecha de reintegro.",
            )
        if fecha_reca is not None and fecha_reintegro < fecha_reca:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"La fecha de reintegro ({_fmt(fecha_reintegro)}) no puede ser anterior "
                    f"a la fecha de la RECA ({_fmt(fecha_reca)})."
                ),
            )
        if fecha_caso is not None and fecha_reintegro < fecha_caso:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"La fecha de reintegro ({_fmt(fecha_reintegro)}) no puede ser anterior "
                    f"a la fecha del caso ({_fmt(fecha_caso)})."
                ),
            )
        if not alta_medica and not alta_psicologica and not tipo_alta:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Para un reintegro total, marca el alta médica, el alta psicológica "
                    "o elige un tipo de alta."
                ),
            )
    # estado=parcial o pendiente: no hay restricciones adicionales aquí


# ── Casos activos y duplicados (QA-003) ───────────────────────────────────
#
# «Caso activo» = estado de reintegro distinto de «total». El reintegro total es el
# estado de cierre del caso (diálogo «Reintegro y cierre del caso»); pendiente y parcial
# siguen abiertos. La pantalla no tiene otro indicador de vigencia.

_ACTIVO = CasoReintegro.estado_reintegro != EstadoReintegro.TOTAL.value


def consulta_casos(
    ingreso_id: int | None = None,
    paciente_id: int | None = None,
    solo_activos: bool = False,
) -> Select:
    stmt = select(CasoReintegro)
    if paciente_id is not None:
        stmt = stmt.join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id).where(
            Ingreso.paciente_id == paciente_id
        )
    if ingreso_id is not None:
        stmt = stmt.where(CasoReintegro.ingreso_id == ingreso_id)
    if solo_activos:
        stmt = stmt.where(_ACTIVO)
    return stmt.order_by(CasoReintegro.id)


def consulta_pacientes_con_casos_activos_repetidos() -> Select:
    """Ids de pacientes (vía su ingreso) con más de un caso activo. Solo lectura."""
    return (
        select(Ingreso.paciente_id)
        .join(CasoReintegro, CasoReintegro.ingreso_id == Ingreso.id)
        .where(_ACTIVO)
        .group_by(Ingreso.paciente_id)
        .having(func.count(CasoReintegro.id) > 1)
    )


def listar_pacientes_con_casos_repetidos(
    db: Session,
) -> list[PacienteConCasosRepetidosRead]:
    ids = consulta_pacientes_con_casos_activos_repetidos().scalar_subquery()
    pacientes = {
        p.id: p
        for p in db.scalars(select(Paciente).where(Paciente.id.in_(ids)))
    }
    filas = db.execute(
        select(CasoReintegro, Ingreso.paciente_id)
        .join(Ingreso, Ingreso.id == CasoReintegro.ingreso_id)
        .where(_ACTIVO, Ingreso.paciente_id.in_(ids))
        .order_by(CasoReintegro.id)
    ).all()
    casos_por_paciente: dict[int, list[CasoActivoResumen]] = {}
    for caso, paciente_id in filas:
        casos_por_paciente.setdefault(paciente_id, []).append(
            CasoActivoResumen.model_validate(caso)
        )
    resultado = [
        PacienteConCasosRepetidosRead(
            paciente_id=pid,
            rut=pacientes[pid].rut,
            nombre=pacientes[pid].nombre,
            casos=casos,
        )
        for pid, casos in casos_por_paciente.items()
        if pid in pacientes
    ]
    resultado.sort(key=lambda r: (r.nombre.lower(), r.paciente_id))
    return resultado


# ── Operaciones con sesión ────────────────────────────────────────────────

def crear_caso_reintegro(db: Session, data: CasoReintegroCreate) -> CasoReintegro:
    """Crea el caso de reintegro vinculado al ingreso (CEPA-040).

    Los datos que el payload no trae se toman del ingreso y su paciente (pueden no
    tenerlos): RUT, sexo y edad del paciente; razón social del ingreso (QA-008).
    """
    ingreso = db.get(Ingreso, data.ingreso_id)
    paciente = db.get(Paciente, ingreso.paciente_id) if ingreso is not None else None
    rut = data.rut
    if rut is None and paciente is not None:
        rut = paciente.rut
    sexo = data.sexo
    if sexo is None and paciente is not None:
        sexo = paciente.sexo
    edad = data.edad
    if edad is None and paciente is not None:
        edad = paciente.edad
    razon_social = (data.razon_social or "").strip() or None
    if razon_social is None and ingreso is not None:
        razon_social = ingreso.razon_social
    caso = CasoReintegro(
        ingreso_id=data.ingreso_id,
        rut=rut,
        nombre=data.nombre,
        tipo_derivacion=data.tipo_derivacion.value,
        fecha_caso=data.fecha_caso,
        sexo=sexo,
        edad=edad,
        region=data.region,
        comuna=data.comuna,
        rubro_empleador=data.rubro_empleador,
        razon_social=razon_social,
        tipo_trabajador=data.tipo_trabajador.value if data.tipo_trabajador else None,
    )
    db.add(caso)
    db.flush()
    return caso


def actualizar_caso_reintegro(
    db: Session, caso: CasoReintegro, data: CasoReintegroUpdate
) -> CasoReintegro:
    """Actualización parcial de datos del caso (CEPA-040 CA-1)."""
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if campo in ("tipo_derivacion", "tipo_trabajador") and valor is not None:
            setattr(caso, campo, valor.value if hasattr(valor, "value") else valor)
        else:
            setattr(caso, campo, valor)
    db.flush()
    return caso


def _obtener_caso_o_404(db: Session, caso_id: int) -> CasoReintegro:
    caso = db.get(CasoReintegro, caso_id)
    if caso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso de reintegro {caso_id} no encontrado.",
        )
    return caso


def crear_reca(db: Session, caso_id: int, data: RecaCreate) -> Reca:
    """Registra la RECA asociada al caso (CEPA-041).

    Valida:
    - Unicidad de numero_reca por caso (RN-1 CEPA-041).
    - Coherencia reca/medidas (validar_coherencia_reca + validar_coherencia_medidas).
    """
    caso = _obtener_caso_o_404(db, caso_id)

    # Unicidad numero_reca por caso (RN-1)
    existente = db.execute(
        select(Reca).where(
            Reca.caso_reintegro_id == caso_id,
            Reca.numero_reca == data.numero_reca,
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una RECA con número {data.numero_reca!r} en este caso (RN-1).",
        )

    validar_coherencia_reca(
        data.solicita_medidas,
        data.detalle_medidas,
        data.fecha_medidas,
        data.verifica_medidas,
        data.fecha_verificacion,
    )
    if data.fecha_medidas is not None:
        validar_coherencia_medidas(data.fecha_reca, data.fecha_medidas, data.fecha_verificacion)

    reca = Reca(
        caso_reintegro_id=caso.id,
        fecha_reca=data.fecha_reca,
        tipo_reca=data.tipo_reca.value,
        numero_reca=data.numero_reca,
        riesgos_calificados=data.riesgos_calificados,
        razon_social=data.razon_social,
        solicita_medidas=data.solicita_medidas,
        detalle_medidas=data.detalle_medidas,
        fecha_medidas=data.fecha_medidas,
        verifica_medidas=data.verifica_medidas,
        detalle_verificacion=data.detalle_verificacion,
        fecha_verificacion=data.fecha_verificacion,
    )
    db.add(reca)
    db.flush()
    return reca


def actualizar_reca(db: Session, reca: Reca, data: RecaUpdate) -> Reca:
    """Actualización parcial de la RECA (CEPA-041)."""
    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        if campo == "tipo_reca" and valor is not None:
            setattr(reca, campo, valor.value if hasattr(valor, "value") else valor)
        else:
            setattr(reca, campo, valor)
    # Re-validar tras actualización
    validar_coherencia_reca(
        reca.solicita_medidas,
        reca.detalle_medidas,
        reca.fecha_medidas,
        reca.verifica_medidas,
        reca.fecha_verificacion,
    )
    if reca.fecha_medidas is not None:
        validar_coherencia_medidas(
            reca.fecha_reca, reca.fecha_medidas, reca.fecha_verificacion
        )
    db.flush()
    return reca


def cerrar_caso_reintegro(
    db: Session, caso: CasoReintegro, data: CierreReintegroUpdate
) -> CasoReintegro:
    """Registra el estado de reintegro y el cierre del caso (CEPA-042).

    Obtiene la fecha_reca desde la RECA asociada (si existe) para la
    validación de coherencia temporal.
    """
    fecha_reca = caso.reca.fecha_reca if caso.reca else None
    validar_coherencia_cierre(
        estado=data.estado_reintegro,
        fecha_reintegro=data.fecha_reintegro,
        fecha_reca=fecha_reca,
        fecha_caso=caso.fecha_caso,
        alta_medica=data.alta_medica,
        alta_psicologica=data.alta_psicologica,
        tipo_alta=data.tipo_alta.value if data.tipo_alta else None,
        fecha_alta_medica=data.fecha_alta_medica,
        fecha_alta_psico=data.fecha_alta_psico,
    )
    caso.estado_reintegro = data.estado_reintegro.value
    caso.fecha_reintegro = data.fecha_reintegro
    caso.remitido_isl = data.remitido_isl
    caso.alta_medica = data.alta_medica
    caso.fecha_alta_medica = data.fecha_alta_medica
    caso.alta_psicologica = data.alta_psicologica
    caso.fecha_alta_psico = data.fecha_alta_psico
    caso.tipo_alta = data.tipo_alta.value if data.tipo_alta else None
    caso.observaciones = data.observaciones
    db.flush()
    return caso
