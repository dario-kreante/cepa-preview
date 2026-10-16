"""Lógica de creación y edición de ingresos (CEPA-010 + CEPA-011, BUG-2608-01)."""

from enum import Enum

from fastapi import HTTPException, status
from sqlalchemy import select, update

from app.audit.service import record_audit
from app.domain.enums import EstadoRegistroPaciente
from app.models.ficha_clinica import FichaClinica
from app.models.imed_payload import ImedPayload
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.schemas.ingreso import IngresoCreate, IngresoUpdate
from app.services.folio import folio_existe, siguiente_folio
from app.services.salutem_sync.borradores import resolver_alerta_borrador


def _aplicar_datos(paciente: Paciente, data: IngresoCreate) -> None:
    paciente.nombre = data.nombre
    paciente.sexo = data.sexo.value
    paciente.edad = data.edad
    paciente.region = data.region
    paciente.comuna = data.comuna
    paciente.telefono = data.telefono
    paciente.correo = data.correo


def _paciente_de_borrador(db, data: IngresoCreate) -> Paciente:
    """Paciente explícito (completar un borrador): debe existir y estar pendiente de folio."""
    paciente = db.get(Paciente, data.paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")
    if paciente.estado_registro != EstadoRegistroPaciente.PENDIENTE_FOLIO.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente no está pendiente de folio.",
        )
    if data.rut is not None and data.rut != paciente.rut:
        otro = db.execute(
            select(Paciente).where(Paciente.rut == data.rut, Paciente.id != paciente.id)
        ).scalar_one_or_none()
        if otro is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El RUT {data.rut} ya pertenece a otro paciente. "
                    "Si es la misma persona, descarta este borrador."
                ),
            )
        paciente.rut = data.rut
    return paciente


def _obtener_o_crear_paciente(db, data: IngresoCreate) -> Paciente:
    """Reutiliza el paciente (por `paciente_id` o por RUT, RN-3); si no existe, lo crea.

    Si existe, actualiza los datos de contacto/demográficos con lo enviado
    (confirmar/actualizar del formulario).
    """
    if data.paciente_id is not None:
        paciente = _paciente_de_borrador(db, data)
    else:
        paciente = db.execute(
            select(Paciente).where(Paciente.rut == data.rut)
        ).scalar_one_or_none()
    if paciente is None:
        paciente = Paciente(rut=data.rut)
        _aplicar_datos(paciente, data)
        db.add(paciente)
        db.flush()
        return paciente
    _aplicar_datos(paciente, data)
    db.flush()
    return paciente


def _dejar_completo(db, paciente: Paciente, actor: str | None) -> None:
    """Un ingreso deja al paciente `completo`: cierra la alerta del borrador o el descarte."""
    anterior = paciente.estado_registro
    if anterior == EstadoRegistroPaciente.COMPLETO.value:
        return
    paciente.estado_registro = EstadoRegistroPaciente.COMPLETO.value
    if anterior == EstadoRegistroPaciente.PENDIENTE_FOLIO.value:
        resolver_alerta_borrador(db, paciente.id)
    else:
        paciente.motivo_descarte = None
        paciente.descartado_por = None
        paciente.descartado_en = None
    db.flush()
    if actor is not None:
        record_audit(
            db, actor=actor, action="UPDATE", entity="paciente", entity_id=str(paciente.id),
            valor_anterior=anterior, valor_nuevo=EstadoRegistroPaciente.COMPLETO.value,
        )


def _resolver_folio(db, data: IngresoCreate, paciente: Paciente) -> tuple[str, bool]:
    """Devuelve (folio, folio_manual).

    - Sin folio: secuencial automático (RN-1).
    - Con folio manual: válido si no colisiona, salvo reingreso explícito del mismo
      paciente (RN-2/RN-3). Una colisión con otro paciente -> 409.
    """
    if data.folio is None:
        return siguiente_folio(db), False

    if folio_existe(db, data.folio):
        existente = db.execute(
            select(Ingreso).where(Ingreso.folio == data.folio).limit(1)
        ).scalar_one()
        # El folio existe: solo se acepta como reingreso EXPLÍCITO del mismo
        # paciente (CEPA-011 RN-3); cualquier otra colisión es 409.
        es_reingreso_valido = data.es_reingreso and existente.paciente_id == paciente.id
        if not es_reingreso_valido:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El folio {data.folio} ya está emitido para otro ingreso.",
            )
    return data.folio, True


def crear_ingreso(db, data: IngresoCreate, actor: str | None = None) -> Ingreso:
    paciente = _obtener_o_crear_paciente(db, data)
    folio, folio_manual = _resolver_folio(db, data, paciente)
    _dejar_completo(db, paciente, actor)
    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio=folio,
        folio_manual=folio_manual,
        numero_siniestro=data.numero_siniestro,
        fecha_ingreso=data.fecha_ingreso,
        fecha_diep_diat=data.fecha_diep_diat,
        tipo_derivacion=data.tipo_derivacion.value,
        tipo_ingreso=data.tipo_ingreso.value,
        modelo_tratamiento=data.modelo_tratamiento,
        diagnostico=data.diagnostico,
        razon_social=data.razon_social,
        # DD-3: dimensiones de reporte
        programa=data.programa,
        tipo_convenio=data.tipo_convenio,
        profesional_id=data.profesional_id,
        especialidad=data.especialidad,
        tipo_atencion=data.tipo_atencion,
    )
    db.add(ingreso)
    db.flush()
    return ingreso


_CAMPOS_PACIENTE = {"nombre", "sexo", "edad", "region", "comuna", "telefono", "correo"}


def actualizar_ingreso(db, ingreso_id: int, data: IngresoUpdate) -> Ingreso:
    """Aplica solo los campos enviados; los del paciente se escriben en el paciente."""
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado.")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if isinstance(valor, Enum):
            valor = valor.value
        destino = ingreso.paciente if campo in _CAMPOS_PACIENTE else ingreso
        setattr(destino, campo, valor)
    db.flush()
    return ingreso


def corregir_folio(db, ingreso_id: int, folio_nuevo: str, actor: str) -> Ingreso:
    """Cambia el folio de un ingreso (corrección de la Administrativa).

    El folio viaja como texto en otras tablas, así que se cambia en bloque: los
    reingresos del mismo paciente que comparten el folio, sus fichas clínicas y los
    datos de IMED. Rechaza un folio que ya use otro paciente. No hace commit.
    """
    ingreso = db.get(Ingreso, ingreso_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado.")
    folio_anterior = ingreso.folio
    if folio_nuevo == folio_anterior:
        return ingreso

    ajeno = db.scalars(
        select(Ingreso.id)
        .where(Ingreso.folio == folio_nuevo, Ingreso.paciente_id != ingreso.paciente_id)
        .limit(1)
    ).first()
    if ajeno is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El folio {folio_nuevo} ya está emitido para otro paciente.",
        )

    db.execute(
        update(Ingreso)
        .where(Ingreso.paciente_id == ingreso.paciente_id, Ingreso.folio == folio_anterior)
        .values(folio=folio_nuevo, folio_manual=True)
        .execution_options(synchronize_session="fetch")
    )
    db.execute(
        update(FichaClinica)
        .where(FichaClinica.folio == folio_anterior)
        .values(folio=folio_nuevo)
        .execution_options(synchronize_session="fetch")
    )
    db.execute(
        update(ImedPayload)
        .where(ImedPayload.folio == folio_anterior)
        .values(folio=folio_nuevo)
        .execution_options(synchronize_session="fetch")
    )
    record_audit(
        db,
        actor=actor,
        action="UPDATE",
        entity="ingreso",
        entity_id=str(ingreso.id),
        valor_anterior=folio_anterior,
        valor_nuevo=folio_nuevo,
    )
    db.flush()
    db.refresh(ingreso)
    return ingreso
