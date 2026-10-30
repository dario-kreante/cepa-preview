"""Listas cerradas del módulo de alertas y notificaciones (EPIC-10).

Se modelan como Enums de str para validar en la capa de aplicación (Pydantic),
manteniendo portabilidad de BD (no se usan tipos enum nativos del motor).
"""

from enum import Enum


class TipoAlerta(str, Enum):
    """Tipos de alerta del motor: los 7 de CEPA-100 más el GAF de licencia (CEPA-075)."""

    CONTROL_MEDICO = "control_medico"
    VENCIMIENTO_LICENCIA = "vencimiento_licencia"
    PLAZO_EPT = "plazo_ept"
    PLAZO_ISL = "plazo_isl"
    CONSENTIMIENTO_PENDIENTE = "consentimiento_pendiente"
    RECETA_POR_RENOVAR = "receta_por_renovar"
    ODA_POR_VENCER = "oda_por_vencer"
    # CEPA-075 / COMP-2609-20: no es un plazo; alerta por tramo de GAF de la licencia.
    GAF_LICENCIA = "gaf_licencia"
    # Alertas del sync de SALUTEM: el médico emitió una licencia o una receta en un control.
    LICENCIA_EN_CONTROL = "licencia_en_control"
    RECETA_EN_CONTROL = "receta_en_control"
    # Paciente borrador creado por el sync: una persona atendida en SALUTEM sin folio en el SIGE.
    PACIENTE_PENDIENTE_FOLIO = "paciente_pendiente_folio"
    # Fase 2 (cita desde SALUTEM): inasistencia a una cita agendada en SALUTEM.
    INASISTENCIA = "inasistencia"
    # Reunión 29-10 (D6): desde la 2.ª inasistencia del paciente (histórico completo),
    # cada inasistencia nueva avisa que hay que revisar si corresponde el encuadre.
    POSIBLE_ENCUADRE = "posible_encuadre"
    # Reunión 29-10 (D9): cita de SALUTEM (agendada o realizada) que ninguna ODA del
    # ingreso cubre: hay que pedir la ODA o su renovación antes de atender o facturar.
    CITA_FUERA_DE_ODA = "cita_fuera_de_oda"
    # Reunión 29-10 (D10): plazo en que el empleador entrega los insumos del informe EPT.
    PLAZO_INSUMOS_EPT = "plazo_insumos_ept"


class EstadoAlerta(str, Enum):
    """Estados del ciclo de vida de una alerta (RN-5 de CEPA-101)."""

    PENDIENTE = "pendiente"
    LEIDA = "leida"
    RESUELTA = "resuelta"


class EstadoTarea(str, Enum):
    """Estados de una tarea operativa (RN-3 de CEPA-103)."""

    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
