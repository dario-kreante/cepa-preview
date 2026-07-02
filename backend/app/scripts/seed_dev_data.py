"""Seed de datos de desarrollo/pruebas para Sistema CEPA, con contexto chileno realista
(Universidad de Talca / Región del Maule) y cobertura de los escenarios de negocio de
cada EPIC (vencimientos, alertas, casos abiertos/cerrados, etc).

No borra datos existentes: genera RUTs/usernames en rangos que evitan colisión y es
seguro de re-ejecutar (agrega más datos en cada corrida).

Uso (desde backend/):
    uv run python -m app.scripts.seed_dev_data
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.audit.service import record_audit
from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.domain.enums import (
    EstadoCaso,
    EstadoConsentimiento,
    EstadoEvaluacion,
    EstadoFarmacologico,
    FrecuenciaFarmaco,
    Sexo,
    TipoAlta,
    TipoDerivacion,
    TipoIngreso,
)
from app.domain.enums_ept import EstadoCumplimiento, EstadoEpt, FactorRiesgo
from app.domain.enums_licencia import EstadoEnvioISL, OrigenLicencia, TipoLicencia
from app.domain.reintegro_enums import EstadoReintegro, TipoReca
from app.models.alerta_licencia import AlertaLicencia  # noqa: F401 (via servicio)
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.cita import Cita
from app.models.consentimiento import Consentimiento
from app.models.control_medico import ControlMedico
from app.models.ept import CasoEpt, ContactoEpt, PlazoEpt, ProcesoEpt
from app.models.farmacos import (
    Alerta,
    EsquemaIndicacion,
    Receta,
    RegistroFarmacologico,
    SeguimTratamiento,
)
from app.models.ficha_clinica import FichaClinica
from app.models.form_definition import FormDefinition
from app.models.imed_payload import ImedPayload
from app.models.ingreso import Ingreso
from app.models.licencia import LicenciaMedica
from app.models.oda import Oda
from app.models.paciente import Paciente
from app.models.plan_tratamiento import PlanTratamiento
from app.models.plazo_programa import PlazoPrograma
from app.models.reintegro import CasoReintegro, Reca
from app.models.seguimiento import Seguimiento
from app.models.tareas import TareaItem
from app.models.usuario import Usuario
from app.models.ventana_proceso import ConfigVentanaProceso
from app.services.alertas import ejecutar_job_alertas
from app.services.farmacos import generar_alertas_revision
from app.services.folio import siguiente_folio
from app.services.form_config import create_draft, publish_version
from app.services.licencias_alerta import generar_alertas_vencimiento
from app.util.rut import _calcular_dv

random.seed(20260701)  # reproducible

HOY = date.today()

# ─────────────────────────────────────────────────────────────────────────────
# Datos contextuales — Chile / Región del Maule (Universidad de Talca)
# ─────────────────────────────────────────────────────────────────────────────

NOMBRES_F = [
    "Camila", "Javiera", "Fernanda", "Constanza", "Valentina", "Catalina",
    "Antonia", "Francisca", "Daniela", "Carolina", "Paula", "Trinidad",
    "Josefa", "Macarena", "Ignacia", "Rocío", "Bárbara", "Natalia", "Andrea",
    "María José", "Ximena", "Soledad", "Pamela", "Claudia", "Marcela",
]
NOMBRES_M = [
    "Matías", "Sebastián", "Diego", "Cristóbal", "Vicente", "Benjamín",
    "Joaquín", "Tomás", "Nicolás", "Felipe", "Ignacio", "Gabriel", "Martín",
    "Agustín", "Maximiliano", "Rodrigo", "Pedro", "Francisco", "Andrés",
    "Eduardo", "Luis", "Carlos", "Jorge", "Manuel", "Álvaro",
]
NOMBRES_OTRO = ["Alex", "Sasha", "Dana", "Robin", "Ariel"]
APELLIDOS = [
    "González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras",
    "Silva", "Martínez", "Sepúlveda", "Morales", "Rodríguez", "López",
    "Fuentes", "Hernández", "Torres", "Araya", "Flores", "Espinoza",
    "Valenzuela", "Castro", "Vásquez", "Reyes", "Gutiérrez", "Núñez",
    "Vargas", "Ramírez", "Tapia", "Cárdenas", "Molina", "Bravo",
    "Riquelme", "Sandoval", "Vera", "Carrasco", "Zúñiga", "Pizarro",
]

# comuna -> región (sesgado a Región del Maule, sede de la Universidad de Talca)
COMUNAS_REGION = (
    [("Talca", "Región del Maule")] * 12
    + [
        ("Curicó", "Región del Maule"),
        ("Linares", "Región del Maule"),
        ("Cauquenes", "Región del Maule"),
        ("Molina", "Región del Maule"),
        ("San Clemente", "Región del Maule"),
        ("Constitución", "Región del Maule"),
        ("Parral", "Región del Maule"),
        ("San Javier", "Región del Maule"),
        ("Villa Alegre", "Región del Maule"),
        ("Romeral", "Región del Maule"),
        ("Pelarco", "Región del Maule"),
        ("Río Claro", "Región del Maule"),
    ]
    + [
        ("Santiago", "Región Metropolitana"),
        ("Providencia", "Región Metropolitana"),
        ("Ñuñoa", "Región Metropolitana"),
        ("Maipú", "Región Metropolitana"),
        ("Puente Alto", "Región Metropolitana"),
    ]
    + [("Chillán", "Región de Ñuble"), ("San Carlos", "Región de Ñuble")]
    + [("Concepción", "Región del Biobío"), ("Los Ángeles", "Región del Biobío")]
    + [("Valparaíso", "Región de Valparaíso"), ("Viña del Mar", "Región de Valparaíso")]
)

RAZONES_SOCIALES = [
    "Universidad de Talca", "Municipalidad de Talca", "Municipalidad de Curicó",
    "Agrícola San Clemente SpA", "Viña Los Robles S.A.", "Frutícola del Maule Ltda.",
    "Forestal Constitución SpA", "Transportes Curicó SpA",
    "Clínica Regional del Maule", "Servicios Sanitarios del Maule S.A.",
    "Sodexo Chile SA", "Empresas CMPC", "Agrocomercial Linares Ltda.",
    "Complejo Forestal Panguilemo", "Supermercados del Maule SpA",
    "Constructora Río Claro Ltda.",
]

DIAGNOSTICOS_CIE10 = [
    "F43.0 Reacción a estrés agudo",
    "F43.1 Trastorno de estrés postraumático",
    "F43.2 Trastornos de adaptación",
    "F41.1 Trastorno de ansiedad generalizada",
    "F41.2 Trastorno mixto ansioso-depresivo",
    "F32.0 Episodio depresivo leve",
    "F32.1 Episodio depresivo moderado",
    "F33.1 Trastorno depresivo recurrente, episodio moderado",
    "F48.0 Neurastenia (síndrome de desgaste laboral)",
    "Z56.9 Problema relacionado con el empleo, no especificado",
]

PROGRAMAS = [
    ("Programa Regular", 30),
    ("PIPT", 45),
    ("Ley Karin", 15),
]

MEDICOS = [
    "Dr. Ricardo Peña Ibarra", "Dra. Consuelo Aguirre Lagos",
    "Dr. Sergio Bustos Cortés", "Dra. Loreto Yáñez Poblete",
]
PSICOLOGOS = [
    "Ps. Verónica Salinas Reyes", "Ps. Cristián Herrera Poblete",
    "Ps. Antonia Ossandón Lira", "Ps. Felipe Cid Sáez",
]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_ruts_usados: set[str] = set()


def rut_valido(cuerpo: int) -> str:
    """Genera un RUT chileno canónico (cuerpo+DV) válido y no repetido en esta corrida."""
    cuerpo_str = str(cuerpo)
    dv = _calcular_dv(cuerpo_str)
    rut = f"{cuerpo_str}{dv}"
    while rut in _ruts_usados:
        cuerpo += 1
        cuerpo_str = str(cuerpo)
        dv = _calcular_dv(cuerpo_str)
        rut = f"{cuerpo_str}{dv}"
    _ruts_usados.add(rut)
    return rut


_rut_counter = [19_000_000]


def siguiente_rut() -> str:
    _rut_counter[0] += random.randint(3, 97)
    return rut_valido(_rut_counter[0])


def nombre_completo(sexo: str) -> tuple[str, str]:
    if sexo == Sexo.F.value:
        nombre = random.choice(NOMBRES_F)
    elif sexo == Sexo.M.value:
        nombre = random.choice(NOMBRES_M)
    else:
        nombre = random.choice(NOMBRES_OTRO)
    ap1, ap2 = random.sample(APELLIDOS, 2)
    return nombre, f"{ap1} {ap2}"


def fecha_aleatoria(desde: date, hasta: date) -> date:
    delta = (hasta - desde).days
    return desde + timedelta(days=random.randint(0, max(delta, 0)))


def dia_habil_en(dias_habiles_desde_hoy: int) -> date:
    """Fecha que cae exactamente a N días hábiles desde hoy (lun-vie), útil para
    disparar deliberadamente las ventanas de alerta (RN-1 CEPA-072, CEPA-100)."""
    cursor = HOY
    contados = 0
    while contados < dias_habiles_desde_hoy:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            contados += 1
    return cursor


def pick_weighted(pairs: list[tuple]) -> object:
    valores, pesos = zip(*pairs)
    return random.choices(valores, weights=pesos, k=1)[0]


# ─────────────────────────────────────────────────────────────────────────────
# Usuarios
# ─────────────────────────────────────────────────────────────────────────────

USUARIOS_SEED = [
    dict(username="cvidal", nombre="Carla Vidal Muñoz", rol="Administrativo",
         email="cvidal@utalca.cl", activo=True),
    dict(username="rsoto", nombre="Rodrigo Soto Espinoza", rol="Administrativo",
         email="rsoto@utalca.cl", activo=True),
    dict(username="pfuentes", nombre="Paulina Fuentes Reyes", rol="Coordinacion",
         email="pfuentes@utalca.cl", activo=True),
    dict(username="mbravo", nombre="Manuel Bravo Tapia", rol="Auditor",
         email="mbravo@utalca.cl", activo=True),
    # Escenario: usuario deshabilitado.
    dict(username="dcarrasco", nombre="Daniela Carrasco Vera", rol="Administrativo",
         email="dcarrasco@utalca.cl", activo=False),
    # Escenario: usuario sin email (se omite en envíos de alerta, CEPA-102).
    dict(username="jgutierrez", nombre="Jorge Gutiérrez Molina", rol="Administrativo",
         email=None, activo=True),
]


def seed_usuarios(db) -> list[Usuario]:
    creados = []
    for datos in USUARIOS_SEED:
        existente = db.execute(
            select(Usuario).where(Usuario.username == datos["username"])
        ).scalar_one_or_none()
        if existente is not None:
            creados.append(existente)
            continue
        u = Usuario(
            username=datos["username"],
            nombre=datos["nombre"],
            hashed_password=hash_password("Cepa2026!"),
            rol=datos["rol"],
            activo=datos["activo"],
            email=datos["email"],
        )
        db.add(u)
        db.flush()
        record_audit(db, actor="seed_dev_data", action="CREATE", entity="usuario",
                      entity_id=str(u.id), rol=u.rol)
        creados.append(u)
    # Escenario: usuario bloqueado por intentos fallidos (CEPA-001 RN-3).
    bloqueado = db.execute(
        select(Usuario).where(Usuario.username == "dcarrasco")
    ).scalar_one_or_none()
    if bloqueado is not None:
        bloqueado.intentos_fallidos = 5
        bloqueado.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.flush()
    print(f"  usuarios: {len(creados)} (incl. preexistentes)")
    return creados


# ─────────────────────────────────────────────────────────────────────────────
# Pacientes + Ingresos (con seguimiento, consentimiento, ODA, ficha clínica)
# ─────────────────────────────────────────────────────────────────────────────

N_PACIENTES = 60


def crear_paciente(db) -> Paciente:
    sexo = pick_weighted([(Sexo.F.value, 55), (Sexo.M.value, 42), (Sexo.OTRO.value, 3)])
    nombre, apellidos = nombre_completo(sexo)
    comuna, region = random.choice(COMUNAS_REGION)
    p = Paciente(
        rut=siguiente_rut(),
        nombre=f"{nombre} {apellidos}",
        sexo=sexo,
        edad=random.randint(18, 64),
        region=region,
        comuna=comuna,
        telefono=f"+569{random.randint(10_000_000, 99_999_999)}",
        correo=f"{nombre.lower().split(' ')[0]}.{apellidos.lower().split(' ')[0]}@mail.com",
    )
    db.add(p)
    db.flush()
    return p


def crear_ingreso(
    db, paciente: Paciente, *, profesional_ids: list[int],
    fecha_min: date, fecha_max: date, folio_override: str | None = None,
) -> Ingreso:
    programa, _ = random.choice(PROGRAMAS)
    tipo_derivacion = random.choice(list(TipoDerivacion)).value
    estado = pick_weighted(
        [(EstadoCaso.ACTIVO.value, 55), (EstadoCaso.CERRADO.value, 30),
         (EstadoCaso.DERIVADO.value, 15)]
    )
    fecha_ingreso = fecha_aleatoria(fecha_min, fecha_max)

    folio = folio_override or siguiente_folio(db)
    ingreso = Ingreso(
        paciente_id=paciente.id,
        folio=folio,
        folio_manual=folio_override is not None,
        numero_siniestro=f"SIN-{random.randint(100000, 999999)}" if random.random() < 0.4 else None,
        fecha_ingreso=fecha_ingreso,
        fecha_diep_diat=fecha_ingreso if tipo_derivacion in ("DIEP", "DIAT") else None,
        tipo_derivacion=tipo_derivacion,
        tipo_ingreso=random.choice(list(TipoIngreso)).value,
        modelo_tratamiento="PIPT" if programa == "PIPT" else "Programa regular",
        diagnostico=random.choice(DIAGNOSTICOS_CIE10),
        razon_social=random.choice(RAZONES_SOCIALES),
        estado=estado,
        programa=programa,
        profesional_id=random.choice(profesional_ids) if random.random() < 0.6 else None,
        tipo_convenio=random.choice(["ISL", "Convenio U.Clinica", "Particular", None]),
        especialidad=random.choice(["Psicología", "Psiquiatría", "Medicina general", None]),
        tipo_atencion=random.choice(["Presencial", "Telemedicina", None]),
        tratamiento_iniciado=random.random() < 0.75,
    )
    if estado in (EstadoCaso.CERRADO.value, EstadoCaso.DERIVADO.value):
        ingreso.tipo_alta = random.choice(list(TipoAlta)).value
        ingreso.fecha_alta = fecha_aleatoria(
            fecha_ingreso + timedelta(days=15), min(HOY, fecha_ingreso + timedelta(days=200))
        )
        ingreso.flag_revision = random.random() < 0.1
        ingreso.observaciones = "Cierre de caso conforme a protocolo institucional."
    db.add(ingreso)
    db.flush()
    return ingreso


def crear_seguimiento_consentimiento_oda_ficha(db, ingreso: Ingreso, programa_dias: dict[str, int]):
    programa = ingreso.programa or "Programa Regular"
    eval_estado = pick_weighted(
        [(EstadoEvaluacion.REALIZADA.value, 65), (EstadoEvaluacion.PENDIENTE.value, 25),
         (EstadoEvaluacion.NO_APLICA.value, 10)]
    )
    seg = Seguimiento(
        ingreso_id=ingreso.id,
        fecha_acogida=ingreso.fecha_ingreso + timedelta(days=random.randint(0, 3)),
        programa=programa,
        eval_medica_estado=eval_estado,
        eval_medica_medico=random.choice(MEDICOS) if eval_estado == "realizada" else None,
        eval_medica_fecha=ingreso.fecha_ingreso + timedelta(days=random.randint(3, 10))
        if eval_estado == "realizada" else None,
        eval_psico_estado=eval_estado,
        eval_psico_psicologo=random.choice(PSICOLOGOS) if eval_estado == "realizada" else None,
        eval_psico_fecha=ingreso.fecha_ingreso + timedelta(days=random.randint(3, 10))
        if eval_estado == "realizada" else None,
        obstaculizacion=random.random() < 0.08,
        plazo_informe=programa_dias.get(programa, 30),
        reca_ep_ec=random.choice(["EP", "EC", None]),
    )
    db.add(seg)

    # Consentimiento: ~15% queda pendiente (dispara CONSENTIMIENTO_PENDIENTE).
    firmado = random.random() < 0.85
    cons = Consentimiento(
        ingreso_id=ingreso.id,
        estado=EstadoConsentimiento.FIRMADO.value if firmado else EstadoConsentimiento.PENDIENTE.value,
        evidencia_ref=f"ficha_clinica:{ingreso.folio}" if firmado else None,
        fecha_firma=ingreso.fecha_ingreso + timedelta(days=1) if firmado else None,
    )
    db.add(cons)

    # ODA: 1-2 por ingreso; algunas por vencer pronto (ODA_POR_VENCER, ventana=7 días calendario).
    n_odas = random.randint(1, 2)
    for i in range(n_odas):
        if i == 0 and random.random() < 0.15:
            venc = HOY + timedelta(days=random.randint(1, 6))  # dentro de ventana
        else:
            venc = fecha_aleatoria(HOY - timedelta(days=30), HOY + timedelta(days=120))
        db.add(Oda(
            ingreso_id=ingreso.id,
            identificador=f"ODA-{ingreso.folio}-{i + 1}",
            fecha_registro=ingreso.fecha_ingreso,
            fecha_vencimiento=venc,
            vigente=(i == n_odas - 1),
        ))

    # Ficha clínica (1-2), contenido modelado sobre la estructura real SALUTEM.
    for _ in range(random.randint(1, 2)):
        contenido = {
            "motivo_consulta": "Síntomas ansiosos y de ánimo asociados a contexto laboral.",
            "sintomas": "Insomnio, irritabilidad, dificultad de concentración.",
            "tiempo_evolucion": f"{random.randint(1, 12)} semanas",
            "antecedentes_morbidos": random.choice(["Sin antecedentes", "Hipotiroidismo", "Migraña"]),
            "examen_mental": {
                "conciencia": "Vigil, lúcido",
                "orientacion": "Orientado en tiempo y espacio",
                "afectividad": random.choice(["Ansiosa", "Deprimida", "Eutímica"]),
                "discurso": "Coherente, curso normal",
            },
            "diagnostico": ingreso.diagnostico,
            "gaf": random.randint(45, 90),
            "indicacion_reposo": random.choice([True, False]),
        }
        db.add(FichaClinica(
            ingreso_id=ingreso.id, folio=ingreso.folio, origen="SALUTEM", contenido=contenido,
        ))
    return seg


# ─────────────────────────────────────────────────────────────────────────────
# Fármacos
# ─────────────────────────────────────────────────────────────────────────────

MEDICAMENTOS = [
    ("Sertralina", "50mg"), ("Escitalopram", "10mg"), ("Quetiapina", "25mg"),
    ("Clonazepam", "0.5mg"), ("Mirtazapina", "15mg"), ("Venlafaxina", "75mg"),
    ("Trazodona", "50mg"), ("Lorazepam", "1mg"),
]


def crear_registro_farmacologico(db, ingreso: Ingreso):
    estado = pick_weighted(
        [(EstadoFarmacologico.ACTIVO.value, 60), (EstadoFarmacologico.SUSPENDIDO.value, 10),
         (EstadoFarmacologico.COMPLETADO.value, 15), (EstadoFarmacologico.PENDIENTE.value, 15)]
    )
    reg = RegistroFarmacologico(
        ingreso_id=ingreso.id,
        medico_tratante=random.choice(MEDICOS),
        estado_farmacologico=estado,
        antecedentes_previos=random.choice(["Sin tratamiento previo", "Tratamiento previo con ISRS"]),
        tratamiento_previo=random.choice([None, "Sertralina 50mg por 6 meses (suspendido)"]),
        activo=estado != EstadoFarmacologico.COMPLETADO.value,
    )
    db.add(reg)
    db.flush()

    n_ind = random.randint(1, 3)
    for i in range(n_ind):
        med, dosis = random.choice(MEDICAMENTOS)
        db.add(EsquemaIndicacion(
            registro_id=reg.id,
            medicamento=med,
            dosis=dosis,
            frecuencia=random.choice(list(FrecuenciaFarmaco)).value,
            extra_sistema=random.random() < 0.1,
            vigente=(i == n_ind - 1),
        ))

    n_recetas = random.randint(1, 3)
    recetas = []
    for i in range(n_recetas):
        emision = fecha_aleatoria(ingreso.fecha_ingreso, HOY)
        if i == n_recetas - 1 and random.random() < 0.35:
            revision = dia_habil_en(random.randint(1, 5))  # dispara alerta receta
            envio = None
        else:
            revision = emision + timedelta(days=random.randint(15, 60))
            envio = revision + timedelta(days=random.randint(0, 3)) if random.random() < 0.6 else None
        r = Receta(
            registro_id=reg.id, fecha_emision=emision, fecha_revision=revision,
            fecha_envio=envio, marca_medicamento=random.choice(MEDICAMENTOS)[0],
        )
        db.add(r)
        recetas.append(r)

    if random.random() < 0.4:
        disminucion = random.random() < 0.5
        cambio = random.random() < 0.4
        db.add(SeguimTratamiento(
            registro_id=reg.id,
            disminucion_farmacos=disminucion,
            plan_disminucion="Reducción gradual 25% cada 2 semanas, control en 1 mes."
            if disminucion else None,
            cambio_esquema=cambio,
            detalle_cambio="Cambio de ISRS por intolerancia gastrointestinal." if cambio else None,
            observaciones="Buena adherencia al tratamiento." if random.random() < 0.5 else None,
        ))
    return reg, recetas


# ─────────────────────────────────────────────────────────────────────────────
# Licencias médicas + controles médicos
# ─────────────────────────────────────────────────────────────────────────────

def crear_licencias(db, ingreso: Ingreso, *, forzar_vencimiento_proximo: bool, forzar_solape: bool):
    n_lm = random.randint(1, 3)
    licencias = []
    cursor_inicio = ingreso.fecha_ingreso + timedelta(days=random.randint(0, 5))
    for i in range(n_lm):
        dias = random.randint(5, 30)
        inicio = cursor_inicio
        termino = inicio + timedelta(days=dias - 1)

        if forzar_vencimiento_proximo and i == n_lm - 1:
            termino = dia_habil_en(random.randint(1, 3))
            inicio = termino - timedelta(days=dias - 1)

        anulada = random.random() < 0.08
        lm = LicenciaMedica(
            ingreso_id=ingreso.id,
            folio_lm=f"LM-{random.randint(1_000_000, 9_999_999)}",
            tipo_lm=random.choice(list(TipoLicencia)).value,
            tipo_reposo=random.choice(["total", "parcial"]),
            fecha_inicio=inicio,
            fecha_termino=termino,
            fecha_emision=inicio - timedelta(days=random.randint(0, 1)),
            inicio_reposo=inicio,
            fin_reposo=termino,
            cantidad_dias=(termino - inicio).days + 1,
            indicacion_reposo="Reposo laboral por cuadro de salud mental.",
            diagnostico=ingreso.diagnostico,
            origen=random.choice([OrigenLicencia.SISTEMA.value, OrigenLicencia.SISTEMA.value,
                                   OrigenLicencia.EXTRA_SISTEMA.value]),
            envio_isl=EstadoEnvioISL.RECHAZADO.value if anulada else random.choice(
                [EstadoEnvioISL.ENVIADO.value, EstadoEnvioISL.PENDIENTE.value]
            ),
            fecha_envio_isl=termino + timedelta(days=2) if not anulada and random.random() < 0.7 else None,
            eeag_gaf=random.randint(40, 85),
            observaciones="Rechazada en ISAPRE/FONASA (77 BIS), en revisión." if anulada else None,
            anulada=anulada,
        )
        db.add(lm)
        db.flush()
        licencias.append(lm)
        cursor_inicio = termino + timedelta(days=random.randint(1, 10))

    # Escenario de solapamiento (CEPA-071 RN-3): dos LM con días calendario en común.
    if forzar_solape and len(licencias) >= 1:
        base = licencias[0]
        solapada = LicenciaMedica(
            ingreso_id=ingreso.id,
            folio_lm=f"LM-{random.randint(1_000_000, 9_999_999)}",
            tipo_lm=base.tipo_lm,
            tipo_reposo="parcial",
            fecha_inicio=base.fecha_inicio + timedelta(days=3),
            fecha_termino=base.fecha_termino + timedelta(days=3),
            fecha_emision=base.fecha_inicio + timedelta(days=3),
            inicio_reposo=base.fecha_inicio + timedelta(days=3),
            fin_reposo=base.fecha_termino + timedelta(days=3),
            cantidad_dias=(base.fecha_termino - base.fecha_inicio) .days + 1,
            indicacion_reposo="Prórroga de reposo con empalme de fechas (revisar acumulado).",
            diagnostico=ingreso.diagnostico,
            origen=OrigenLicencia.SISTEMA.value,
            envio_isl=EstadoEnvioISL.PENDIENTE.value,
            eeag_gaf=random.randint(40, 85),
            anulada=False,
        )
        db.add(solapada)
        db.flush()
        licencias.append(solapada)

    return licencias


def crear_controles_medicos(db, ingreso: Ingreso, licencias: list[LicenciaMedica]):
    n_controles = random.randint(1, 3)
    for i in range(n_controles):
        fecha_control = fecha_aleatoria(ingreso.fecha_ingreso, HOY)
        tiene_licencia = len(licencias) > 0 and random.random() < 0.6
        lm_ref = random.choice(licencias) if tiene_licencia else None

        proximo_agendado = random.random() < 0.5
        if i == n_controles - 1 and not proximo_agendado and random.random() < 0.3:
            proximo_control = HOY + timedelta(days=random.randint(1, 6))  # dispara CONTROL_MEDICO
        else:
            proximo_control = fecha_control + timedelta(days=random.randint(14, 45))

        db.add(ControlMedico(
            ingreso_id=ingreso.id,
            fecha_control=fecha_control,
            semana_control=max((fecha_control - ingreso.fecha_ingreso).days // 7 + 1, 1),
            medico_tratante=random.choice(MEDICOS),
            region_derivacion=ingreso.paciente.region if ingreso.paciente else "Región del Maule",
            proximo_control=proximo_control,
            proximo_agendado=proximo_agendado,
            tiene_licencia=tiene_licencia,
            resumen_termino_lm=f"LM {lm_ref.folio_lm} vigente hasta {lm_ref.fecha_termino.isoformat()}."
            if lm_ref else None,
            total_dias_lm=lm_ref.cantidad_dias if lm_ref else None,
            tipo_licencia=lm_ref.tipo_lm if lm_ref else None,
            tipo_reposo=lm_ref.tipo_reposo if lm_ref else None,
            gaf=lm_ref.eeag_gaf if lm_ref else random.randint(45, 90),
            estado_reca=random.choice(["pendiente", "aprobado", "en_proceso", "no_aplica"]),
            observaciones="Evolución favorable, mantiene indicaciones." if random.random() < 0.5 else None,
        ))


# ─────────────────────────────────────────────────────────────────────────────
# EPT
# ─────────────────────────────────────────────────────────────────────────────

def crear_caso_ept(db, ingreso: Ingreso, paciente: Paciente):
    corresponde = random.random() < 0.85
    caso = CasoEpt(
        ingreso_id=ingreso.id,
        mes=ingreso.fecha_ingreso.strftime("%Y-%m"),
        fecha_ingreso_ept=ingreso.fecha_ingreso,
        nombre_trabajador=paciente.nombre,
        rut_trabajador=paciente.rut,
        region_trabajador=paciente.region,
        eista=random.choice(["Marcela Iturra Poblete", "Cristián Muñoz Delgado", "Andrea Bello Fuentes"]),
        factor_riesgo=random.choice(list(FactorRiesgo)).value,
        corresponde_ept=corresponde,
        estado=EstadoEpt.ABIERTO.value if corresponde else EstadoEpt.NO_CORRESPONDE.value,
        razon_social=ingreso.razon_social,
        unidad_cargo_horario="Área operaciones / turno diurno",
    )
    db.add(caso)
    db.flush()

    for i in range(random.randint(1, 2)):
        db.add(ContactoEpt(caso_ept_id=caso.id, correo=f"contacto{i + 1}.{caso.id}@empresa.cl"))

    if corresponde:
        hay_testigos = random.random() < 0.6
        db.add(ProcesoEpt(
            caso_ept_id=caso.id,
            plazo_evid_denunciante=ingreso.fecha_ingreso + timedelta(days=10),
            plazo_insumos_empresa=ingreso.fecha_ingreso + timedelta(days=15),
            hay_testigos=hay_testigos,
            testigos_cantidad=random.randint(1, 3) if hay_testigos else 0,
            num_entrevistas=random.randint(0, 5),
            insumos_eista="Informe de entrevistas y antecedentes laborales adjuntos.",
            observaciones=None,
        ))

        estado_informe = pick_weighted(
            [(EstadoCumplimiento.EN_PLAZO.value, 35), (EstadoCumplimiento.POR_VENCER.value, 20),
             (EstadoCumplimiento.VENCIDO.value, 15), (EstadoCumplimiento.CUMPLIDO.value, 30)]
        )
        if estado_informe == EstadoCumplimiento.POR_VENCER.value:
            plazo_informe = dia_habil_en(random.randint(1, 5))  # dispara PLAZO_EPT
        elif estado_informe == EstadoCumplimiento.VENCIDO.value:
            plazo_informe = HOY - timedelta(days=random.randint(1, 20))
        else:
            plazo_informe = HOY + timedelta(days=random.randint(10, 60))

        plazo_isl = dia_habil_en(random.randint(1, 5)) if random.random() < 0.2 else HOY + timedelta(
            days=random.randint(10, 60)
        )

        db.add(PlazoEpt(
            caso_ept_id=caso.id,
            plazo_informe_ept=plazo_informe,
            plazo_portal_isl=plazo_isl,
            fecha_entrega_isl=plazo_isl - timedelta(days=1)
            if estado_informe == EstadoCumplimiento.CUMPLIDO.value else None,
            fecha_envio=plazo_informe - timedelta(days=1)
            if estado_informe == EstadoCumplimiento.CUMPLIDO.value else None,
            estado_informe=estado_informe,
            estado_entrega_isl=estado_informe,
        ))
    return caso


# ─────────────────────────────────────────────────────────────────────────────
# Reintegro
# ─────────────────────────────────────────────────────────────────────────────

_reca_counter = [1]


def crear_caso_reintegro(db, ingreso: Ingreso, paciente: Paciente):
    estado = pick_weighted(
        [(EstadoReintegro.PENDIENTE.value, 40), (EstadoReintegro.PARCIAL.value, 30),
         (EstadoReintegro.TOTAL.value, 30)]
    )
    fecha_caso = ingreso.fecha_ingreso + timedelta(days=random.randint(5, 30))
    caso = CasoReintegro(
        ingreso_id=ingreso.id,
        rut=paciente.rut,
        nombre=paciente.nombre,
        tipo_derivacion=ingreso.tipo_derivacion,
        fecha_caso=fecha_caso,
        sexo=paciente.sexo,
        edad=paciente.edad,
        region=paciente.region,
        comuna=paciente.comuna,
        rubro_empleador=random.choice(
            ["Agricultura", "Educación superior", "Servicios de salud", "Comercio",
             "Industria forestal", "Transporte", "Construcción", "Administración pública"]
        ),
        estado_reintegro=estado,
        remitido_isl=random.random() < 0.7,
        alta_medica=estado != EstadoReintegro.PENDIENTE.value and random.random() < 0.6,
        alta_psicologica=estado != EstadoReintegro.PENDIENTE.value and random.random() < 0.6,
        observaciones=None,
    )
    if estado == EstadoReintegro.TOTAL.value:
        caso.fecha_reintegro = fecha_caso + timedelta(days=random.randint(30, 120))
        caso.tipo_alta = random.choice(list(TipoAlta)).value
    if caso.alta_medica:
        caso.fecha_alta_medica = fecha_caso + timedelta(days=random.randint(20, 90))
    if caso.alta_psicologica:
        caso.fecha_alta_psico = fecha_caso + timedelta(days=random.randint(20, 90))
    db.add(caso)
    db.flush()

    if random.random() < 0.75:
        solicita = random.random() < 0.5
        verifica = solicita and random.random() < 0.6
        fecha_reca = fecha_caso + timedelta(days=random.randint(5, 20))
        fecha_medidas = fecha_reca + timedelta(days=random.randint(5, 15)) if solicita else None
        _reca_counter[0] += 1
        db.add(Reca(
            caso_reintegro_id=caso.id,
            fecha_reca=fecha_reca,
            tipo_reca=random.choice(list(TipoReca)).value,
            numero_reca=f"RECA-2026-{_reca_counter[0]:05d}",
            riesgos_calificados="Exposición a factores de riesgo psicosocial en el puesto de trabajo.",
            razon_social=ingreso.razon_social or random.choice(RAZONES_SOCIALES),
            solicita_medidas=solicita,
            detalle_medidas="Rotación de funciones y ajuste de carga laboral." if solicita else None,
            fecha_medidas=fecha_medidas,
            verifica_medidas=verifica,
            detalle_verificacion="Medidas implementadas y verificadas en terreno." if verifica else None,
            fecha_verificacion=fecha_medidas + timedelta(days=random.randint(10, 30)) if verifica else None,
        ))
    return caso


# ─────────────────────────────────────────────────────────────────────────────
# Plan de tratamiento + citas
# ─────────────────────────────────────────────────────────────────────────────

def crear_plan_y_citas(db, ingreso: Ingreso):
    if random.random() < 0.7:
        db.add(PlanTratamiento(
            ingreso_id=ingreso.id,
            sesiones_plan=random.randint(6, 20),
            aumentos_isl=random.choice([0, 0, 0, 2, 4]),
        ))

    n_citas = random.randint(2, 6)
    fecha_cursor = ingreso.fecha_ingreso
    for _ in range(n_citas):
        fecha_cursor += timedelta(days=random.randint(3, 14))
        if fecha_cursor > HOY + timedelta(days=30):
            break
        estado = "agendada" if fecha_cursor > HOY else pick_weighted(
            [("realizada", 70), ("inasistencia", 20), ("anulada", 10)]
        )
        db.add(Cita(ingreso_id=ingreso.id, estado=estado, fecha=fecha_cursor))


# ─────────────────────────────────────────────────────────────────────────────
# Configuración (tareas, ventanas de proceso, plazos por programa, formularios, IMED)
# ─────────────────────────────────────────────────────────────────────────────

TIPOS_TAREA = [
    "gestionar_receta", "enviar_informe", "verificar_medidas",
    "agendar_control", "revisar_consentimiento",
]


def seed_tareas(db, usuarios: list[Usuario], ingresos: list[Ingreso]):
    administrativos = [u for u in usuarios if u.rol == "Administrativo" and u.activo]
    if not administrativos:
        return
    for _ in range(25):
        usuario = random.choice(administrativos)
        ingreso = random.choice(ingresos)
        completada = random.random() < 0.4
        tarea = TareaItem(
            titulo=f"{random.choice(TIPOS_TAREA).replace('_', ' ').capitalize()} — folio {ingreso.folio}",
            descripcion="Tarea generada por seed de datos de desarrollo.",
            estado="completada" if completada else random.choice(["pendiente", "en_progreso"]),
            tipo_tarea=random.choice(TIPOS_TAREA),
            caso_id=ingreso.id,
            caso_tipo="ingreso",
            usuario_id=usuario.id,
            completada_en=datetime.now(timezone.utc) if completada else None,
            completada_por=usuario.username if completada else None,
        )
        db.add(tarea)
    print("  tarea_item: 25")


def seed_config_ventana_proceso(db, creador: str):
    # Columnas visibles = encabezados reales de la planilla administrativa CEPA
    # (Anexo 4, María del Pilar García Zerene, UTalca — 11-mar-2026).
    ventanas = {
        "licencias": ["Región", "Paciente", "Rut", "Folio", "Días", "Inicio", "Termino",
                      "Tipo Reposo", "Tipo LM", "Envio a ISL", "EEAG", "Fecha Emisión LM"],
        "farmacos": ["Folio", "Mes", "Región de derivación", "Nombre del paciente", "Rut",
                     "Médico Tratante", "Estado", "Fecha receta", "Fecha Revisión Receta",
                     "Fecha Envío Receta", "Marca"],
        "auditoria": ["Folio (peritaje)", "Número de siniestro", "Fecha denuncia",
                      "Nombre Paciente", "RUT", "Diagnóstico", "Licencia médica", "Estado"],
        "reintegro": ["Folio", "Derivación", "Fecha", "Nombre", "RUT", "Región", "RECA",
                      "N° RECA", "Reintegro", "Fecha Reintegro", "Estado"],
        "controles": ["Folio", "Región de derivación", "Paciente", "Rut", "Médico Tratante",
                      "Semana Control", "Licencia Si/No", "Total dias de LM", "GAF"],
    }
    for proceso, columnas in ventanas.items():
        existe = db.execute(
            select(ConfigVentanaProceso).where(ConfigVentanaProceso.proceso == proceso)
        ).scalar_one_or_none()
        if existe is not None:
            continue
        db.add(ConfigVentanaProceso(
            proceso=proceso, columnas_visibles=columnas,
            orden_por_defecto=columnas[0], creado_por=creador,
        ))
    print(f"  config_ventana_proceso: {len(ventanas)}")


def seed_plazo_programa(db):
    for programa, dias in PROGRAMAS:
        existe = db.get(PlazoPrograma, programa)
        if existe is None:
            db.add(PlazoPrograma(programa=programa, dias_plazo_informe=dias))
    print(f"  plazo_programa: {len(PROGRAMAS)}")


def seed_formularios(db, username: str):
    existente = db.execute(
        select(FormDefinition).where(FormDefinition.form_key == "ingresos")
    ).scalar_one_or_none()
    if existente is not None:
        print("  form_definition/version/field: ya existía 'ingresos', se omite")
        return

    class _Payload:
        def __init__(self, fields):
            self.fields = fields

    class _Field:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    campos = [
        _Field(field_key="folio", label="Folio", field_type="text", required=True,
               system_locked=True, domain_values=None, display_order=1, active=True),
        _Field(field_key="fecha_ingreso", label="Fecha de ingreso", field_type="date",
               required=True, system_locked=True, domain_values=None, display_order=2, active=True),
        _Field(field_key="tipo_derivacion", label="Tipo de derivación", field_type="select",
               required=True, system_locked=False,
               domain_values=[t.value for t in TipoDerivacion], display_order=3, active=True),
        _Field(field_key="diagnostico", label="Diagnóstico", field_type="text", required=True,
               system_locked=False, domain_values=None, display_order=4, active=True),
    ]
    version = create_draft(db, "ingresos", _Payload(campos), username)
    publish_version(db, "ingresos", version.id, username)
    print("  form_definition/version/field: 1 formulario ('ingresos') publicado")


def seed_imed_payloads(db, ingresos: list[Ingreso]):
    muestras = random.sample(ingresos, min(6, len(ingresos)))
    for ingreso in muestras:
        tipo = random.choice(["licencia_medica", "receta_electronica"])
        datos = (
            {"folio_lm": f"LM-{random.randint(1_000_000, 9_999_999)}", "rut": "N/A",
             "dias": random.randint(5, 20), "tipo": random.choice(["1", "5", "6"])}
            if tipo == "licencia_medica"
            else {"folio_receta": f"RE-{random.randint(100000, 999999)}",
                  "medicamento": random.choice(MEDICAMENTOS)[0]}
        )
        db.add(ImedPayload(folio=ingreso.folio, tipo=tipo, datos=datos))
    print(f"  imed_payload: {len(muestras)}")


# ─────────────────────────────────────────────────────────────────────────────
# Orquestación
# ─────────────────────────────────────────────────────────────────────────────

def main():
    db = SessionLocal()
    try:
        print("Sembrando datos de desarrollo — Sistema CEPA (contexto Chile / Región del Maule)")

        usuarios = seed_usuarios(db)
        admin = next((u for u in usuarios if u.username == "cvidal"), usuarios[0])
        profesional_ids = [u.id for u in usuarios if u.rol in ("Administrativo", "Coordinacion")]
        programa_dias = dict(PROGRAMAS)

        seed_plazo_programa(db)
        seed_config_ventana_proceso(db, admin.username)
        seed_formularios(db, admin.username)

        pacientes: list[Paciente] = []
        ingresos: list[Ingreso] = []

        fecha_min, fecha_max = date(2025, 8, 1), HOY - timedelta(days=1)

        for idx in range(N_PACIENTES):
            paciente = crear_paciente(db)
            pacientes.append(paciente)

            ingreso1 = crear_ingreso(
                db, paciente, profesional_ids=profesional_ids,
                fecha_min=fecha_min, fecha_max=fecha_max,
            )
            ingresos.append(ingreso1)

            # ~15% de los pacientes tiene un reingreso (mantiene folio anterior, CEPA-011 RN-2).
            if random.random() < 0.15:
                reingreso = crear_ingreso(
                    db, paciente, profesional_ids=profesional_ids,
                    fecha_min=ingreso1.fecha_ingreso + timedelta(days=30), fecha_max=HOY,
                    folio_override=ingreso1.folio,
                )
                reingreso.tipo_derivacion = random.choice(
                    [TipoDerivacion.REINGRESO_FUMP.value, TipoDerivacion.REINGRESO_SUSESO.value]
                )
                ingresos.append(reingreso)

        db.flush()
        print(f"  pacientes: {len(pacientes)}")
        print(f"  ingresos: {len(ingresos)}")

        forzados_vencimiento = set(random.sample(range(len(ingresos)), min(8, len(ingresos))))
        forzados_solape = set(random.sample(range(len(ingresos)), min(4, len(ingresos))))

        n_farmaco = n_lm = n_ctrl = n_ept = n_reintegro = 0
        for i, ingreso in enumerate(ingresos):
            crear_seguimiento_consentimiento_oda_ficha(db, ingreso, programa_dias)

            if ingreso.tratamiento_iniciado and random.random() < 0.7:
                crear_registro_farmacologico(db, ingreso)
                n_farmaco += 1

            if random.random() < 0.75:
                licencias = crear_licencias(
                    db, ingreso,
                    forzar_vencimiento_proximo=i in forzados_vencimiento,
                    forzar_solape=i in forzados_solape,
                )
                n_lm += len(licencias)
                if licencias and random.random() < 0.7:
                    crear_controles_medicos(db, ingreso, licencias)
                    n_ctrl += 1

            if ingreso.tipo_derivacion in (
                TipoDerivacion.DIEP.value, TipoDerivacion.DIAT.value,
                TipoDerivacion.PAPT.value, TipoDerivacion.PAPT_FLUJO_AT.value,
            ) and random.random() < 0.5:
                crear_caso_ept(db, ingreso, ingreso.paciente)
                n_ept += 1

            if random.random() < 0.5:
                crear_caso_reintegro(db, ingreso, ingreso.paciente)
                n_reintegro += 1

            crear_plan_y_citas(db, ingreso)

            if (i + 1) % 20 == 0:
                db.flush()
                print(f"  ... procesados {i + 1}/{len(ingresos)} ingresos")

        db.flush()
        print(f"  registros farmacológicos: ~{n_farmaco}")
        print(f"  licencias médicas: {n_lm}")
        print(f"  controles médicos: ~{n_ctrl}")
        print(f"  casos EPT: {n_ept}")
        print(f"  casos reintegro: {n_reintegro}")

        seed_tareas(db, usuarios, ingresos)
        seed_imed_payloads(db, ingresos)

        record_audit(db, actor="seed_dev_data", action="CREATE", entity="seed_dev_data",
                      entity_id=None, valor_nuevo=f"{len(pacientes)} pacientes, {len(ingresos)} ingresos")
        db.commit()
        print("Commit de datos base OK.")

        # Motores reales de alertas — se ejecutan igual que el job programado (CEPA-072/CEPA-022/CEPA-100).
        nuevas_lm = generar_alertas_vencimiento(db)
        db.commit()
        print(f"  alerta_licencia generadas (motor real CEPA-072): {len(nuevas_lm)}")

        nuevas_receta = generar_alertas_revision(db)
        db.commit()
        print(f"  alerta (fármacos, motor real CEPA-022 RN-3) generadas: {len(nuevas_receta)}")

        total_notif = ejecutar_job_alertas(db, actor="seed_dev_data")
        print(f"  alerta_notif generadas (motor real CEPA-100): {total_notif}")

        print("Seed completado.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
