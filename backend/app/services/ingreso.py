"""Lógica de creación de ingresos (CEPA-010 + CEPA-011)."""

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.schemas.ingreso import IngresoCreate
from app.services.folio import folio_existe, siguiente_folio


def _obtener_o_crear_paciente(db, data: IngresoCreate) -> Paciente:
    """Reutiliza el paciente si el RUT ya existe (RN-3); si no, lo crea.

    Si existe, actualiza los datos de contacto/demográficos con lo enviado
    (confirmar/actualizar del formulario).
    """
    paciente = db.execute(
        select(Paciente).where(Paciente.rut == data.rut)
    ).scalar_one_or_none()
    if paciente is None:
        paciente = Paciente(
            rut=data.rut,
            nombre=data.nombre,
            sexo=data.sexo.value,
            edad=data.edad,
            region=data.region,
            comuna=data.comuna,
            telefono=data.telefono,
            correo=data.correo,
        )
        db.add(paciente)
        db.flush()
        return paciente
    # actualizar datos del paciente existente
    paciente.nombre = data.nombre
    paciente.sexo = data.sexo.value
    paciente.edad = data.edad
    paciente.region = data.region
    paciente.comuna = data.comuna
    paciente.telefono = data.telefono
    paciente.correo = data.correo
    db.flush()
    return paciente


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
        # El folio existe: solo permitir si es reingreso del MISMO paciente
        if existente.paciente_id != paciente.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El folio {data.folio} ya está emitido para otro ingreso.",
            )
        # Reingreso del mismo paciente: se permite (sea explícito o no)
    return data.folio, True


def crear_ingreso(db, data: IngresoCreate) -> Ingreso:
    paciente = _obtener_o_crear_paciente(db, data)
    folio, folio_manual = _resolver_folio(db, data, paciente)
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
    )
    db.add(ingreso)
    db.flush()
    return ingreso
