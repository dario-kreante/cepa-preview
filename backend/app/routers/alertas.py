"""Router de alertas unificadas (EPIC-10, CEPA-100, CEPA-101, CEPA-102)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agendamiento.salutem import lotes
from app.audit.service import record_audit
from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.domain.proyeccion_reintegro import opcion_alertable, texto_alerta
from app.models.alertas import AlertaNotif
from app.models.cita import Cita
from app.models.control_medico import ControlMedico
from app.models.ept import CasoEpt, PlazoEpt
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro
from app.schemas.alertas import AlertaRead, AlertaUpdate, JobResultado
from app.services.alertas import ejecutar_job_alertas
from app.services.alertas_contexto import AlertaContextoRead, contexto_de_alerta

router = APIRouter(prefix="/api/v1/alertas", tags=["alertas"])

_writer = require_role("Administrativo", "Coordinacion")
_reader = require_role("Administrativo", "Coordinacion", "Auditor")



def _visible_para(alerta: AlertaNotif, current_user) -> bool:
    """Una Administrativa ve (y gestiona) sus alertas y las sin destinatario (panel general)."""
    return current_user.role != "Administrativo" or alerta.usuario_id in (None, current_user.id)


# Transiciones de estado válidas (DD-E)
_TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    EstadoAlerta.PENDIENTE.value: {EstadoAlerta.LEIDA.value, EstadoAlerta.RESUELTA.value},
    EstadoAlerta.LEIDA.value: {EstadoAlerta.RESUELTA.value},
    EstadoAlerta.RESUELTA.value: set(),  # estado terminal
}


@router.post(
    "/ejecutar-job",
    response_model=JobResultado,
    dependencies=[Depends(_writer)],
)
def ejecutar_job(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResultado:
    """Ejecuta el job de revisión de plazos perentorios (CEPA-100 RN-2).

    DD-B: la auditoría se registra ANTES del commit dentro del servicio.
    """
    generadas = ejecutar_job_alertas(db, actor=current_user.username)
    return JobResultado(alertas_generadas=generadas, timestamp=datetime.now(timezone.utc))


@router.get("", response_model=list[AlertaRead], dependencies=[Depends(_reader)])
def listar_alertas(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertaRead]:
    """Panel de notificaciones in-app: devuelve alertas filtradas por rol y asignación.

    - Administrativo: sus alertas (usuario_id == current_user.id) y las sin destinatario
      (usuario_id nulo, panel general), que de otro modo solo vería Coordinación.
    - Coordinacion/Auditor: todas las alertas (alcance ampliado, RN-2/RN-3 CEPA-101).
    """
    stmt = select(AlertaNotif)
    if current_user.role == "Administrativo":
        stmt = stmt.where(
            or_(AlertaNotif.usuario_id == current_user.id, AlertaNotif.usuario_id.is_(None))
        )
    stmt = stmt.order_by(AlertaNotif.generada_en.desc())
    alertas = list(db.scalars(stmt))
    pacientes = _pacientes_de_casos(db, alertas)
    casos_ept = _casos_ept_de_alertas(db, alertas)
    nombres = _nombres_de_pacientes(db, set(pacientes.values()))
    detalles = _detalles_de_alertas(db, alertas)
    resultado = []
    for a in alertas:
        paciente_id = pacientes.get((a.caso_tipo, a.caso_id))
        resultado.append(
            AlertaRead.model_validate(a).model_copy(
                update={
                    "paciente_id": paciente_id,
                    "paciente_nombre": nombres.get(paciente_id),
                    "caso_ept_id": casos_ept.get((a.caso_tipo, a.caso_id)),
                    "detalle": detalles.get(a.id),
                }
            )
        )
    return resultado


def _detalles_de_alertas(db: Session, alertas: list[AlertaNotif]) -> dict[int, str]:
    """Texto propio de cada alerta que lo tiene: la proyección de reintegro del control.

    ``alerta_notif`` no guarda el valor: se lee del control al listar. Si el médico corrigió
    la proyección, la alerta del valor anterior ya quedó resuelta (ver alertas_control).
    QA-010: con una opción de la lista que alerta, el texto suma el plazo estimado (fecha del
    control + 7/14/21 días) o «seguimiento» para el reintegro parcial.
    """
    de_proyeccion = [
        a for a in alertas
        if a.tipo == TipoAlerta.PROYECCION_REINTEGRO.value and a.caso_tipo == "control_medico"
    ]
    controles: dict[int, tuple] = {}
    for lote in lotes({a.caso_id for a in de_proyeccion}):
        filas = db.execute(
            select(ControlMedico.id, ControlMedico.proyeccion_reintegro, ControlMedico.fecha_control)
            .where(ControlMedico.id.in_(lote))
        ).all()
        controles.update({cid: (valor, fecha) for cid, valor, fecha in filas})
    detalles: dict[int, str] = {}
    for a in de_proyeccion:
        valor, fecha = controles.get(a.caso_id, (None, None))
        if not valor:
            continue
        opcion = opcion_alertable(valor)
        detalles[a.id] = texto_alerta(opcion, fecha) if opcion is not None and fecha else valor
    return detalles


def _casos_ept_de_alertas(db: Session, alertas: list[AlertaNotif]) -> dict[tuple[str, int], int]:
    """Caso EPT real de cada alerta: las de plazo (caso_tipo "ept") guardan el id del PlazoEpt;
    las de insumos (caso_tipo "caso_ept") ya guardan el id del CasoEpt."""
    casos: dict[tuple[str, int], int] = {}
    for lote in lotes({a.caso_id for a in alertas if a.caso_tipo == "ept"}):
        filas = db.execute(select(PlazoEpt.id, PlazoEpt.caso_ept_id).where(PlazoEpt.id.in_(lote)))
        casos.update({("ept", plazo_id): caso_id for plazo_id, caso_id in filas})
    for lote in lotes({a.caso_id for a in alertas if a.caso_tipo == "caso_ept"}):
        existentes = db.scalars(select(CasoEpt.id).where(CasoEpt.id.in_(lote)))
        casos.update({("caso_ept", caso_id): caso_id for caso_id in existentes})
    return casos


def _nombres_de_pacientes(db: Session, ids: set[int]) -> dict[int, str]:
    nombres: dict[int, str] = {}
    for lote in lotes(ids):
        nombres.update(db.execute(select(Paciente.id, Paciente.nombre).where(Paciente.id.in_(lote))).all())
    return nombres


def _pacientes_de_casos(db: Session, alertas: list[AlertaNotif]) -> dict[tuple[str, int], int]:
    """Paciente de cada caso que cuelga de un ingreso (ODA, ingreso, cita de SALUTEM): una consulta por tipo."""
    odas = {a.caso_id for a in alertas if a.caso_tipo == "oda"}
    ingresos = {a.caso_id for a in alertas if a.caso_tipo == "ingreso"}
    pacientes: dict[tuple[str, int], int] = {}
    if odas:
        filas = db.execute(
            select(Oda.id, Ingreso.paciente_id)
            .join(Ingreso, Ingreso.id == Oda.ingreso_id)
            .where(Oda.id.in_(odas))
        )
        pacientes.update({("oda", oda_id): pid for oda_id, pid in filas})
    if ingresos:
        filas = db.execute(select(Ingreso.id, Ingreso.paciente_id).where(Ingreso.id.in_(ingresos)))
        pacientes.update({("ingreso", ing_id): pid for ing_id, pid in filas})
    # Casos EPT (por plazo o por caso, ver _casos_ept_de_alertas): paciente vía el ingreso del caso.
    casos_ept = _casos_ept_de_alertas(db, alertas)
    for lote in lotes(set(casos_ept.values())):
        filas = db.execute(
            select(CasoEpt.id, Ingreso.paciente_id)
            .join(Ingreso, Ingreso.id == CasoEpt.ingreso_id)
            .where(CasoEpt.id.in_(lote))
        )
        por_caso = dict(filas.all())
        pacientes.update(
            {clave: por_caso[caso_id] for clave, caso_id in casos_ept.items() if caso_id in por_caso}
        )
    # Casos con ingreso propio: licencia, control médico y caso de reintegro (QA-003).
    for tipo, modelo in (
        ("licencia", LicenciaMedica),
        ("control_medico", ControlMedico),
        ("caso_reintegro", CasoReintegro),
    ):
        ids = {a.caso_id for a in alertas if a.caso_tipo == tipo}
        for lote in lotes(ids):
            filas = db.execute(
                select(modelo.id, Ingreso.paciente_id)
                .join(Ingreso, Ingreso.id == modelo.ingreso_id)
                .where(modelo.id.in_(lote))
            )
            pacientes.update({(tipo, caso_id): pid for caso_id, pid in filas})
    citas_salutem = {a.caso_id for a in alertas if a.caso_tipo == "salutem_cita"}
    for lote in lotes(citas_salutem):
        filas = db.execute(
            select(Cita.salutem_cita_id, Ingreso.paciente_id)
            .join(Ingreso, Ingreso.id == Cita.ingreso_id)
            .where(Cita.salutem_cita_id.in_(lote))
        )
        pacientes.update({("salutem_cita", cita_id): pid for cita_id, pid in filas})
    return pacientes


@router.get(
    "/{alerta_id}/contexto", response_model=AlertaContextoRead, dependencies=[Depends(_reader)]
)
def contexto_alerta(
    alerta_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertaContextoRead:
    """Paciente, ingreso y cita de SALUTEM de la alerta, para gestionarla desde el panel."""
    alerta = db.get(AlertaNotif, alerta_id)
    if alerta is None or not _visible_para(alerta, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")
    return contexto_de_alerta(db, alerta)


@router.patch("/{alerta_id}", response_model=AlertaRead, dependencies=[Depends(_writer)])
def actualizar_estado_alerta(
    alerta_id: int,
    payload: AlertaUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertaNotif:
    """Marca una alerta como leída o resuelta (CA-4 CEPA-101).

    Valida transiciones (DD-E): pendiente→leida→resuelta (y pendiente→resuelta).
    Rechaza transición desde resuelta (422).
    DD-B: auditoría ANTES del commit.
    """
    alerta = db.get(AlertaNotif, alerta_id)
    # Una alerta asignada a otra Administrativa no existe para esta (mismo criterio que el listado).
    if alerta is None or not _visible_para(alerta, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada")

    estado_actual = alerta.estado
    estado_nuevo = payload.estado.value

    # Validar transición (DD-E)
    permitidos = _TRANSICIONES_VALIDAS.get(estado_actual, set())
    if estado_nuevo not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Transición no permitida: {estado_actual!r} → {estado_nuevo!r}. "
                f"Transiciones válidas desde '{estado_actual}': {sorted(permitidos) or 'ninguna'}."
            ),
        )

    alerta.estado = estado_nuevo
    if payload.estado == EstadoAlerta.RESUELTA:
        alerta.resuelta_en = datetime.now(timezone.utc)
    elif payload.estado != EstadoAlerta.RESUELTA:
        # Al regresar de resuelta (si fuera posible) limpiaríamos resuelta_en;
        # actualmente es terminal pero dejamos el campo intacto intencionalmente.
        pass

    # DD-B: auditoría ANTES del commit
    record_audit(
        db,
        actor=current_user.username,
        action="UPDATE",
        entity="alerta_notif",
        entity_id=str(alerta_id),
    )
    db.commit()
    db.refresh(alerta)
    return alerta


@router.post(
    "/enviar-correos",
    response_model=JobResultado,
    dependencies=[Depends(_writer)],
)
def enviar_correos(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobResultado:
    """Envía correos de alerta a los responsables (CEPA-102 P1, D12).

    DD-C:
    - Si smtp_host está vacío: retorna inmediatamente con enviados=0 y
      omitidas=N SIN marcar email_enviado (FakeEmailSender nunca se usa
      en la ruta de producción).
    - Las alertas sin usuario o sin email en Usuario.email se cuentan como omitidas.
    No reenvía correos ya enviados (CA-4).
    DD-B: auditoría ANTES del commit dentro del servicio.
    """
    from app.config import get_settings
    from app.services.alertas import enviar_correos_alertas

    settings = get_settings()
    smtp_host = getattr(settings, "smtp_host", "")

    if not smtp_host:
        # Contar alertas pendientes de envío para reportar omitidas (DD-C)
        from sqlalchemy import func
        omitidas = db.scalar(
            select(func.count()).select_from(AlertaNotif).where(
                AlertaNotif.email_enviado == False,  # noqa: E712
                AlertaNotif.estado.in_(["pendiente", "leida"]),
            )
        ) or 0
        return JobResultado(
            alertas_generadas=0,
            omitidas=omitidas,
            timestamp=datetime.now(timezone.utc),
        )

    from app.services.email_sender import SmtpConfig, SmtpEmailSender

    config = SmtpConfig(
        host=smtp_host,
        port=getattr(settings, "smtp_port", 587),
        username=getattr(settings, "smtp_username", ""),
        password=getattr(settings, "smtp_password", ""),
        use_tls=getattr(settings, "smtp_use_tls", True),
        from_addr=getattr(settings, "smtp_from_addr", "cepa-alertas@utalca.cl"),
    )
    sender = SmtpEmailSender(config)

    resultado = enviar_correos_alertas(db, sender=sender, actor=current_user.username)
    return JobResultado(
        alertas_generadas=resultado["enviados"],
        omitidas=resultado["omitidas"],
        timestamp=datetime.now(timezone.utc),
    )
