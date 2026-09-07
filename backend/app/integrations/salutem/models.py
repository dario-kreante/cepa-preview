"""DTOs de la integración SALUTEM (capa anticorrupción).

Estos objetos aíslan al dominio CEPA de las rarezas del payload de SALUTEM:
claves en camelCase, nombres que cambian entre endpoints (`citaHoraInicio` en
`/cita` vs `citaHorarioInicio` en `/atencion`) y bloques clínicos cuya forma
depende de la especialidad.

El contenido clínico NO se modela campo a campo: varía demasiado entre
especialidades (una atención oftalmológica trae bloques de refracción que una
de medicina general no tiene). Se conserva crudo en `contenido`, que es lo que
termina en `FichaClinica.contenido`.
"""

from datetime import date
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class EstadoCitaSalutem(IntEnum):
    """Estados de cita de SALUTEM.

    `/cita` exige este parámetro pese a que la documentación lo presenta como
    opcional: sin él responde ERROR_ESTADO_ID_NO_INGRESADO.
    """

    AGENDADO = 1
    ANULADO = 2
    ATENDIDO = 3
    AGENDADO_WEB = 4
    CONFIRMADO = 5
    CONFIRMADO_WEB = 6
    CONFIRMADO_EMAIL = 7
    RECEPCIONADO = 8
    NO_ASISTE = 9


class TipoFechaCita(IntEnum):
    """Sobre qué fecha filtra `/cita`: la de la cita o la de su creación."""

    FECHA_CITA = 1
    FECHA_CREACION = 2


class PersonaSalutem(BaseModel):
    """Persona de SALUTEM, resuelta a partir del RUT del paciente CEPA."""

    model_config = ConfigDict(frozen=True)

    salutem_id: int
    identificacion: str | None = None
    tipo_identificacion: str | None = None
    nombres: str | None = None
    apellidos: str | None = None
    # SALUTEM entrega la fecha de nacimiento como "DD-MM-YYYY", no ISO. Se deja
    # como string para no adivinar el formato en el borde de la integración.
    fecha_nacimiento: str | None = None
    sexo: str | None = None
    comuna: str | None = None
    financiador: str | None = None
    crudo: dict[str, Any] = {}

    @classmethod
    def desde_api(cls, d: dict[str, Any]) -> "PersonaSalutem":
        return cls(
            salutem_id=int(d["SALUTEM_ID"]),
            identificacion=d.get("identificacion"),
            tipo_identificacion=d.get("tipoIdentificacion"),
            nombres=d.get("nombres"),
            apellidos=d.get("apellidos"),
            fecha_nacimiento=d.get("fechaNacimiento"),
            sexo=d.get("sexo"),
            comuna=d.get("comuna"),
            financiador=d.get("financiador"),
            crudo=d,
        )


class CitaSalutem(BaseModel):
    """Cita de SALUTEM. Sirve tanto para `/cita` como para el listado de `/atencion`."""

    model_config = ConfigDict(frozen=True)

    persona_id: int
    cita_id: int
    cita_token: str | None = None
    fecha: date | None = None
    hora_inicio: str | None = None
    estado_id: int | None = None
    estado_nombre: str | None = None
    especialidad_nombre: str | None = None
    profesional_nombre: str | None = None
    sucursal_nombre: str | None = None
    financiador_nombre: str | None = None
    crudo: dict[str, Any] = {}

    @classmethod
    def desde_api(cls, d: dict[str, Any]) -> "CitaSalutem":
        # `/cita` usa citaHoraInicio; `/atencion` usa citaHorarioInicio para lo mismo.
        hora = d.get("citaHoraInicio") or d.get("citaHorarioInicio")
        fecha_cruda = d.get("citaFecha")
        return cls(
            persona_id=int(d["personaId"]),
            cita_id=int(d["citaId"]),
            cita_token=d.get("citaToken"),
            fecha=date.fromisoformat(fecha_cruda) if fecha_cruda else None,
            hora_inicio=hora,
            estado_id=d.get("estadoCitaId"),
            estado_nombre=d.get("estadoCitaNombre"),
            especialidad_nombre=d.get("especialidadNombre"),
            profesional_nombre=d.get("profesionalNombre"),
            sucursal_nombre=d.get("sucursalNombre"),
            financiador_nombre=d.get("financiadorNombre"),
            crudo=d,
        )


class AtencionSalutem(BaseModel):
    """Atención completa: la cita más el contenido clínico crudo."""

    model_config = ConfigDict(frozen=True)

    cita: CitaSalutem
    contenido: dict[str, Any]

    @classmethod
    def desde_api(cls, d: dict[str, Any]) -> "AtencionSalutem":
        return cls(cita=CitaSalutem.desde_api(d), contenido=d)
