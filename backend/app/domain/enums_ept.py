"""Enums del dominio EPT (EPIC-03).

Listas cerradas validadas en la capa de aplicación (Pydantic).
Columnas correspondientes usan String(40) para portabilidad (D15).
"""

from enum import Enum


class FactorRiesgo(str, Enum):
    """Factor de riesgo del puesto laboral (CEPA-030 RN-1).

    Lista cerrada que usa el área EPT de UTalca (QA UTalca 22-10, QA-003).
    Es la única que se acepta al crear o editar un caso. El orden de los
    miembros es el orden en que se muestran en la UI (las etiquetas viven en
    el frontend). Los valores son slugs ASCII de hasta 40 caracteres porque la
    columna ``caso_ept.factor_riesgo`` es String(40) sin check constraint.
    """

    SOBRECARGA = "sobrecarga"
    SUBCARGA = "subcarga"
    TRABAJO_ACTIVO_CONTINUO = "trabajo_activo_continuo"
    AUSENCIA_DESCANSOS = "ausencia_descansos"
    TAREAS_RUTINARIAS = "tareas_rutinarias"
    TRABAJO_EMOCIONALMENTE_COMPROMETIDO = "trabajo_emocionalmente_comprometido"
    AMBIGUEDAD_CONFLICTO_ROLES = "ambiguedad_conflicto_roles"
    LIMITACION_REGULAR_TRABAJO = "limitacion_regular_trabajo"
    LIMITACION_TOMAR_DECISIONES = "limitacion_tomar_decisiones"
    LIMITACION_REGULAR_PERMISOS = "limitacion_regular_permisos"
    CARENCIA_USO_HABILIDADES = "carencia_uso_habilidades"
    AUSENCIA_AYUDA_INFORMACION = "ausencia_ayuda_informacion"
    AUSENCIA_CAPACITACION_TECNOLOGICA = "ausencia_capacitacion_tecnologica"
    CONFLICTOS_INTERPERSONALES = "conflictos_interpersonales"
    CONDICIONES_ORGANIZACIONALES_ESTRESANTES = "condiciones_organizacionales_estresantes"
    HOSTILIDAD_PARES = "hostilidad_pares"
    HOSTILIDAD_SUBALTERNOS = "hostilidad_subalternos"
    DISFUNCIONALIDAD_JEFATURA = "disfuncionalidad_jefatura"
    HOSTILIDAD_JEFATURA = "hostilidad_jefatura"
    ASEDIO_SEXUAL = "asedio_sexual"
    VIOLENCIA_ACOSO_USUARIOS = "violencia_acoso_usuarios"
    VIOLENCIA_PERSONAS_AJENAS = "violencia_personas_ajenas"
    CONDICIONES_FISICAS_ERGONOMICAS = "condiciones_fisicas_ergonomicas"
    NO_APLICA = "no_aplica"


class FactorRiesgoLegado(str, Enum):
    """Factores de riesgo genéricos de la primera versión (deprecados).

    Hay casos guardados con estos valores en las BD de dev/QA. Se aceptan solo
    en lectura (``CasoEptRead``) para que esos casos se sigan mostrando; crear
    o editar un caso exige un valor de ``FactorRiesgo``. No se migran los datos
    porque no hay equivalencia 1 a 1 con la lista nueva: al editar el caso, el
    usuario elige el factor nuevo.
    """

    CARGA = "carga"
    ORGANIZACION_TRABAJO = "organizacion_trabajo"
    FACTORES_PSICOSOCIALES = "factores_psicosociales"
    VIOLENCIA_LABORAL = "violencia_laboral"
    CONDICIONES_ERGONOMICAS = "condiciones_ergonomicas"
    OTRO = "otro"


class EstadoEpt(str, Enum):
    """Estado del caso EPT."""

    ABIERTO = "abierto"
    NO_CORRESPONDE = "no_corresponde"
    CERRADO = "cerrado"


class EstadoCumplimiento(str, Enum):
    """Estado de cumplimiento de un plazo regulatorio EPT (CEPA-032 RN-1)."""

    EN_PLAZO = "en_plazo"
    POR_VENCER = "por_vencer"
    VENCIDO = "vencido"
    CUMPLIDO = "cumplido"
