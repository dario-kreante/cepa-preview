# Alertas de licencia y receta desde SALUTEM — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cuando el sync de SALUTEM crea o actualiza un control médico con licencia o receta, la
encargada recibe una alerta y puede abrir desde el CEPA los documentos que el médico subió a la
biblioteca de SALUTEM ese día.

**Architecture:** Las alertas salen del formulario de la atención (señales puras sobre el
`contenido`) y se crean en la vinculación del sync, en el motor existente `alerta_notif`. La
biblioteca de SALUTEM se lista en cada ciclo `caliente` para las personas con controles recientes
y se guarda solo la metadata en `salutem_archivo`. Los archivos se unen al control por fecha y se
descargan bajo demanda a través del backend, sin copia.

**Tech Stack:** FastAPI + SQLAlchemy 2 + Alembic (Postgres en tests, Oracle 19c en la VM),
httpx, pytest; React 19 + TS + TanStack Query + openapi-fetch, Vitest + MSW 2.

**Spec:** `docs/superpowers/specs/2026-10-15-alertas-licencia-receta-salutem-design.md`

## Global Constraints

- Solo lectura sobre SALUTEM (v4 D12): ningún método nuevo del cliente escribe; los nombres evitan create/update/delete/push/write/patch.
- Portabilidad D15: identificadores ≤ 30 caracteres en minúscula, tipos genéricos, PK `BigInteger` sin `Identity` cuando la clave viene de SALUTEM.
- Oracle: comparar booleanos con `== false()`, nunca `.is_(False)` (ORA-00908).
- El CEPA no guarda el contenido de los archivos: ni en BD ni en disco.
- Una alerta por control y tipo, para siempre; solo controles con `fecha_control` dentro de los últimos 14 días (`DIAS_NOVEDAD = 14`).
- Archivos unidos al control: `fecha_creacion` en `[fecha_control, min(siguiente control del ingreso, fecha_control + 7 días))`.
- Textos visibles al usuario en español. Títulos de alerta: "Licencia emitida en control" y "Receta emitida en control".
- Commits en español, Conventional Commits, terminando con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Desviaciones de la spec (decididas al planificar)

1. **`tiene_licencia` del control no cambia.** El extractor de licencias exige "licencia" o "LM" y no reconoce el certificado "debe permanecer en reposo…". En vez de cambiar `controles._licencia`, la alerta de licencia usa `control.tiene_licencia or certificado_reposo(contenido)`.
2. **El contenido se sirve bajo el control:** `GET /api/v1/controles-medicos/{control_id}/archivos/{archivo_id}/contenido`, no `/api/v1/salutem/archivos/{id}/contenido`. Así se autoriza con los permisos del control y solo se entregan archivos unidos a él.
3. **Al hacer clic en la alerta se abre un diálogo** con el control y sus documentos, en vez de navegar a `/controles?control=`. La pantalla de Controles busca por paciente, y llegar a un control concreto requeriría resolver paciente e ingreso. El diálogo tiene un botón "Ir a Controles".
4. **La biblioteca se lista solo en el ciclo `caliente`, después de la vinculación.** Así cubre los controles recién creados en el mismo ciclo, sin una llamada extra al crearlos.

## Review Focus

- La re-vinculación completa (`fria`/`backfill` re-aplican todas las atenciones) no debe crear alertas de controles antiguos: el corte `DIAS_NOVEDAD` se prueba en la Tarea 2.
- `archivo_base64` vacío (la copia de QA no tiene los binarios viejos) debe responder 404 "SALUTEM no entregó el contenido", no 500: se prueba en las Tareas 3 y 5.
- `fechaCreacion` con formato inesperado no debe romper el ciclo: el archivo se guarda con fecha nula y no se une a ningún control (Tarea 4).
- Una caída de SALUTEM al listar archivos de una persona no debe abortar el ciclo ni perder la vinculación ya hecha (Tarea 4); una credencial rechazada sí aborta, como en el resto del sync.
- Un archivo de otra persona, o de fuera de la ventana del control, no se debe poder descargar por el endpoint del control (Tarea 5).

## Preparación del entorno (una vez, antes de la Tarea 1)

El worktree no trae entornos propios. Se usan los del repo principal:

```bash
export PY="/Users/darioramirez/Proyectos Dev/CEPA Preview/backend/.venv/bin"
cd "/Users/darioramirez/Proyectos Dev/CEPA Preview/.claude/worktrees/salutem-licenses-recovery-c7c829/frontend" && npm ci
```

Los tests de backend usan el Postgres local (`cepa_test`, ya corriendo). Se corren desde `backend/` del worktree con `"$PY/pytest"`.

---

### Tarea 1: Señales de licencia y receta en el formulario

**Files:**
- Create: `backend/app/integrations/salutem/senales.py`
- Modify: `backend/app/services/farmacos_sugeridos.py:34-50` (mueve `_es_receta`, `_es_campo_indicaciones`, `_recetas` a `senales`)
- Test: `backend/tests/test_salutem_senales.py`

**Interfaces:**
- Produces: `certificado_reposo(contenido: dict) -> bool`, `registros_receta(contenido: dict) -> list[Any]`, `tiene_receta(contenido: dict) -> bool` en `app.integrations.salutem.senales`.

- [ ] **Step 1: Write the failing test**

```python
"""Señales de licencia y receta en el formulario de una atención de SALUTEM."""

from app.integrations.salutem.senales import certificado_reposo, registros_receta, tiene_receta

CERTIFICADO = (
    "El médico que suscribe certifica asistir profesionalmente al(la) \r\n<br>paciente X \r\n"
    "<br>quien debe permanecer en reposo desde el\r\n<br>15-04-2024 hasta el ____, "
)


def test_el_certificado_de_reposo_es_una_indicacion_documento():
    contenido = {"indicaciones": [{"tipo": "Documento", "nombre": "Documentos", "registro": CERTIFICADO}]}
    assert certificado_reposo(contenido) is True


def test_un_documento_que_no_habla_de_reposo_no_es_certificado():
    contenido = {"indicaciones": [{"tipo": "Documento", "nombre": "Documentos", "registro": "Certificado de asistencia"}]}
    assert certificado_reposo(contenido) is False


def test_reposo_fuera_de_un_documento_no_cuenta_como_certificado():
    contenido = {"indicaciones": [{"tipo": "Indicación", "nombre": "Indicación General", "registro": "reposo relativo"}]}
    assert certificado_reposo(contenido) is False


def test_receta_medicamentos_con_farmacos_es_receta():
    contenido = {"indicaciones": [{"tipo": "Receta Medicamentos", "nombre": "Receta",
                                   "registro": "Sertralina 50 mg (comprimido)\r\n 1 comprimido al día"}]}
    assert tiene_receta(contenido) is True


def test_el_campo_indicaciones_con_farmacos_es_receta():
    contenido = {"antecedentes": [{"agrupacion": "", "nombre": "Indicaciones",
                                   "registro": "Clotiazepam 5 mg 0-0-1"}]}
    assert tiene_receta(contenido) is True


def test_sin_farmacos_no_hay_receta():
    contenido = {"indicaciones": [{"tipo": "Indicación", "nombre": "Indicación General", "registro": "Control en 15 días"}]}
    assert tiene_receta(contenido) is False
    assert registros_receta(contenido) == []


def test_contenido_vacio_no_tiene_senales():
    assert certificado_reposo({}) is False
    assert tiene_receta({}) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"$PY/pytest" tests/test_salutem_senales.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.integrations.salutem.senales'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/integrations/salutem/senales.py`:

```python
"""Señales de licencia y receta en el formulario de una atención de SALUTEM.

Funciones puras sobre el `contenido` crudo de la atención: no tocan la base ni la red.
Las usan las alertas de los controles creados desde SALUTEM y los fármacos sugeridos.

- El certificado de reposo es una indicación de tipo "Documento" que SALUTEM genera
  ("…debe permanecer en reposo desde el … hasta el …"). El extractor de licencias no lo
  reconoce porque no dice "licencia" ni "LM".
- La receta es una indicación con "receta" en el tipo ("Receta Medicamentos", "Receta")
  o el campo "Indicaciones" del formulario del CEPA, cuando menciona algún fármaco.
"""

import html
import re
from typing import Any

from app.integrations.salutem.campos import items
from app.integrations.salutem.farmacos import extraer_farmacos

_RE_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_REPOSO = re.compile(r"\breposo\b", re.IGNORECASE)


def _texto(registro: Any) -> str:
    if not isinstance(registro, str):
        return ""
    return _RE_TAG.sub("", _RE_BR.sub("\n", html.unescape(registro)))


def _indicaciones(contenido: dict[str, Any]) -> list[dict[str, Any]]:
    valor = contenido.get("indicaciones") or []
    if isinstance(valor, dict):
        valor = [valor]
    return [i for i in valor if isinstance(i, dict)]


def certificado_reposo(contenido: dict[str, Any]) -> bool:
    """True si la atención trae el certificado de reposo que genera SALUTEM."""
    return any(
        str(i.get("tipo") or "").strip().casefold() == "documento"
        and _RE_REPOSO.search(_texto(i.get("registro")))
        for i in _indicaciones(contenido)
    )


def _es_receta(indicacion: Any) -> bool:
    if not isinstance(indicacion, dict):
        return False
    # SALUTEM separa por tipo: "Receta Medicamentos" (con nombre "Receta" o
    # "Indicaciones de tratamiento farmacológico"), "Indicación", "Documento"...
    return "receta" in str(indicacion.get("tipo") or "").casefold()


def _es_campo_indicaciones(item: dict[str, Any]) -> bool:
    # El campo "Indicaciones" del formulario del CEPA, en la sección que sea.
    return str(item.get("nombre") or "").strip().casefold() == "indicaciones"


def registros_receta(contenido: dict[str, Any]) -> list[Any]:
    """Los textos de la atención donde el médico escribe la receta."""
    return [
        i.get("registro") for i in items(contenido) if _es_receta(i) or _es_campo_indicaciones(i)
    ]


def tiene_receta(contenido: dict[str, Any]) -> bool:
    """True si alguno de esos textos menciona al menos un fármaco."""
    return any(extraer_farmacos(r) for r in registros_receta(contenido))
```

En `backend/app/services/farmacos_sugeridos.py`, borrar `_es_receta`, `_es_campo_indicaciones` y `_recetas` (líneas 34-50), agregar el import y reemplazar el uso:

```python
from app.integrations.salutem.senales import registros_receta
```

```python
        for registro_receta in registros_receta(contenido):
```

Si `items` ya no se usa en `farmacos_sugeridos.py`, quitar su import.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"$PY/pytest" tests/test_salutem_senales.py tests/test_farmacos_sugeridos_api.py tests/test_salutem_extraccion_farmacos.py -q`
Expected: PASS (los de fármacos sugeridos siguen verdes: el cambio es solo de lugar).

Si `test_el_campo_indicaciones_con_farmacos_es_receta` falla porque `extraer_farmacos` no entiende "Clotiazepam 5 mg 0-0-1", usar en el test un texto que ya cubre `tests/test_salutem_extraccion_farmacos.py` (copiar uno de sus casos de notación mañana-tarde-noche) en vez de cambiar el extractor.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/salutem/senales.py backend/app/services/farmacos_sugeridos.py backend/tests/test_salutem_senales.py
git commit -m "feat(salutem): señales de licencia y receta en el formulario de la atención

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 2: Alertas de licencia y receta al vincular un control

**Files:**
- Modify: `backend/app/domain/enums_alertas.py:10-21` (dos tipos nuevos)
- Modify: `backend/app/services/alertas.py:179-191` (`VENTANAS_DEFAULT`)
- Create: `backend/app/services/salutem_sync/alertas_control.py`
- Modify: `backend/app/services/salutem_sync/controles.py:71-99` (`sincronizar_control`)
- Modify: `backend/app/services/salutem_sync/vinculacion.py:99` (pasa `hoy`)
- Test: `backend/tests/salutem_sync/test_alertas_control.py`

**Interfaces:**
- Consumes: `certificado_reposo`, `tiene_receta` (Tarea 1).
- Produces: `TipoAlerta.LICENCIA_EN_CONTROL = "licencia_en_control"`, `TipoAlerta.RECETA_EN_CONTROL = "receta_en_control"`; `alertar_control(db, control, contenido, hoy) -> int`; `resolver_alertas_control(db, control_id) -> None`; `sincronizar_control(db, atencion, ingreso, *, hoy: date)`.

- [ ] **Step 1: Write the failing test**

`backend/tests/salutem_sync/test_alertas_control.py`:

```python
"""Alertas de licencia y receta emitidas en un control creado desde SALUTEM.

El fixture AHORA es 2026-09-16 (Santiago): las atenciones recientes van el 2026-09-10.
"""

from datetime import date

from sqlalchemy import select

from app.integrations.salutem.models import AtencionSalutem, EstadoCitaSalutem, PersonaSalutem
from app.models.alertas import AlertaNotif
from app.models.config_alerta import ConfigAlerta
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.services.salutem_sync import copia
from app.services.salutem_sync.vinculacion import vincular
from tests.salutem_sync.conftest import AHORA

PERSONA = 1216099
ATENDIDO = int(EstadoCitaSalutem.ATENDIDO)
LICENCIA = {"antecedentes": [{"agrupacion": "", "nombre": "Indicación de reposo",
                              "registro": "Se extiende LM tipo 6 por 30 días"}]}
RECETA = {"indicaciones": [{"tipo": "Receta Medicamentos", "nombre": "Receta",
                            "registro": "Sertralina 50 mg (comprimido)\r\n 1 comprimido al día"}]}
CERTIFICADO = {"indicaciones": [{"tipo": "Documento", "nombre": "Documentos",
                                 "registro": "quien debe permanecer en reposo desde el 10-09-2026"}]}


def _ingreso(db) -> Ingreso:
    paciente = Paciente(rut="390000099", nombre="Paciente Alerta", sexo="F", edad=40,
                        region="Maule", salutem_persona_id=PERSONA)
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(paciente_id=paciente.id, folio="F-2026-0099", folio_manual=True,
                      fecha_ingreso=date(2026, 8, 1), tipo_derivacion="DIEP", tipo_ingreso="convenio",
                      modelo_tratamiento="ambulatorio", diagnostico="prueba", estado="activo")
    db.add(ingreso)
    db.flush()
    copia.guardar_persona(db, PersonaSalutem.desde_api({"SALUTEM_ID": PERSONA, "identificacion": "390000099"}), AHORA)
    return ingreso


def _atencion(db, cita_id, fecha="2026-09-10", estado=ATENDIDO, **contenido):
    copia.guardar_atencion(db, AtencionSalutem.desde_api({
        "personaId": PERSONA, "citaId": cita_id, "citaFecha": fecha, "estadoCitaId": estado,
        "estadoCitaNombre": "Atendido", "especialidadNombre": "Médico/a",
        "profesionalNombre": "DRA. PAULA ROJAS", **contenido,
    }), AHORA)


def _alertas(db) -> list[AlertaNotif]:
    return list(db.scalars(select(AlertaNotif).order_by(AlertaNotif.tipo)))


def test_control_nuevo_con_licencia_y_receta_crea_una_alerta_de_cada_tipo(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7001, **LICENCIA, **RECETA)

    vincular(db_session, AHORA)

    [control] = db_session.scalars(select(ControlMedico)).all()
    alertas = _alertas(db_session)
    assert [a.tipo for a in alertas] == ["licencia_en_control", "receta_en_control"]
    for a in alertas:
        assert (a.caso_tipo, a.caso_id, a.estado, a.ventana_dias) == ("control_medico", control.id, "pendiente", 0)
        assert a.plazo_objetivo.date() == date(2026, 9, 10)


def test_el_certificado_de_reposo_alerta_licencia(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7002, **CERTIFICADO)

    vincular(db_session, AHORA)

    assert [a.tipo for a in _alertas(db_session)] == ["licencia_en_control"]


def test_control_sin_licencia_ni_receta_no_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7003)

    vincular(db_session, AHORA)

    assert _alertas(db_session) == []


def test_al_cambiar_la_atencion_no_se_duplica_la_alerta(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7004, **LICENCIA)
    vincular(db_session, AHORA)
    _atencion(db_session, 7004, **LICENCIA, evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)

    assert len(_alertas(db_session)) == 1


def test_una_alerta_resuelta_no_reaparece(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7005, **LICENCIA)
    vincular(db_session, AHORA)
    [a] = _alertas(db_session)
    a.estado = "resuelta"
    db_session.flush()
    _atencion(db_session, 7005, **LICENCIA, evolucionTratamiento=[{"nombre": "E", "registro": "cambio"}])

    vincular(db_session, AHORA)

    assert [x.estado for x in _alertas(db_session)] == ["resuelta"]


def test_un_control_antiguo_no_alerta(db_session):
    """Una re-vinculación completa no debe inundar de alertas por controles viejos."""
    _ingreso(db_session)
    _atencion(db_session, 7006, fecha="2026-08-20", **LICENCIA)  # 27 días antes de AHORA

    vincular(db_session, AHORA, todo=True)

    assert db_session.scalars(select(ControlMedico)).first() is not None
    assert _alertas(db_session) == []


def test_tipo_apagado_en_la_configuracion_no_alerta(db_session):
    _ingreso(db_session)
    db_session.add(ConfigAlerta(tipo="receta_en_control", dias=0, habiles=False, activo=False))
    db_session.flush()
    _atencion(db_session, 7007, **LICENCIA, **RECETA)

    vincular(db_session, AHORA)

    assert [a.tipo for a in _alertas(db_session)] == ["licencia_en_control"]


def test_al_anularse_la_atencion_sus_alertas_quedan_resueltas(db_session):
    _ingreso(db_session)
    _atencion(db_session, 7008, **LICENCIA)
    vincular(db_session, AHORA)
    _atencion(db_session, 7008, estado=int(EstadoCitaSalutem.ANULADO), **LICENCIA)

    vincular(db_session, AHORA)

    [a] = _alertas(db_session)
    assert a.estado == "resuelta"
    assert a.resuelta_en is not None
```

Antes de correrlo, revisar `backend/app/models/config_alerta.py`: si `ConfigAlerta` exige más columnas (por ejemplo `actualizado_por`), agregarlas al constructor del test.

- [ ] **Step 2: Run test to verify it fails**

Run: `"$PY/pytest" tests/salutem_sync/test_alertas_control.py -q`
Expected: FAIL (no se crean alertas: `assert [] == ['licencia_en_control', 'receta_en_control']`).

- [ ] **Step 3: Write minimal implementation**

`backend/app/domain/enums_alertas.py`, al final de `TipoAlerta`:

```python
    # Alertas del sync de SALUTEM: el médico emitió una licencia o una receta en un control.
    LICENCIA_EN_CONTROL = "licencia_en_control"
    RECETA_EN_CONTROL = "receta_en_control"
```

`backend/app/services/alertas.py`, dentro de `VENTANAS_DEFAULT`:

```python
    # Sin plazo: se crean en el sync al vincular el control; aquí solo se encienden o apagan.
    TipoAlerta.LICENCIA_EN_CONTROL.value: {"dias": 0, "habiles": False},
    TipoAlerta.RECETA_EN_CONTROL.value: {"dias": 0, "habiles": False},
```

`backend/app/services/salutem_sync/alertas_control.py`:

```python
"""Alertas de licencia y receta emitidas en un control creado desde SALUTEM.

Se crean en la vinculación del sync, no en el job diario: llegan con el retraso del
sync (~5 min). Una por control y tipo para siempre: si el médico corrige la atención no
se repite, y si la encargada la resolvió no reaparece. Solo para controles recientes
(DIAS_NOVEDAD): `fria` y `backfill` re-vinculan todo, y sin este corte un despliegue
llenaría el panel con controles de hace meses.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.domain.enums_alertas import EstadoAlerta, TipoAlerta
from app.integrations.salutem.senales import certificado_reposo, tiene_receta
from app.models.alertas import AlertaNotif
from app.models.control_medico import ControlMedico
from app.services.alertas import _resolver_usuario
from app.services.config_alertas import cargar_ventanas

ACTOR = "salutem-sync"
CASO_TIPO = "control_medico"
DIAS_NOVEDAD = 14
TIPOS = (TipoAlerta.LICENCIA_EN_CONTROL.value, TipoAlerta.RECETA_EN_CONTROL.value)


def alertar_control(db: Session, control: ControlMedico, contenido: dict[str, Any], hoy: date) -> int:
    """Crea las alertas que falten para este control. Devuelve cuántas creó."""
    if control.fecha_control < hoy - timedelta(days=DIAS_NOVEDAD):
        return 0
    senales = {
        TipoAlerta.LICENCIA_EN_CONTROL.value: bool(control.tiene_licencia) or certificado_reposo(contenido),
        TipoAlerta.RECETA_EN_CONTROL.value: tiene_receta(contenido),
    }
    if not any(senales.values()):
        return 0
    ventanas = cargar_ventanas(db)
    existentes = set(
        db.scalars(
            select(AlertaNotif.tipo).where(
                AlertaNotif.caso_tipo == CASO_TIPO,
                AlertaNotif.caso_id == control.id,
                AlertaNotif.tipo.in_(TIPOS),
            )
        )
    )
    creadas = 0
    for tipo, hay in senales.items():
        if not hay or tipo in existentes or not ventanas.get(tipo, {}).get("activo", True):
            continue
        db.add(
            AlertaNotif(
                tipo=tipo,
                estado=EstadoAlerta.PENDIENTE.value,
                caso_id=control.id,
                caso_tipo=CASO_TIPO,
                usuario_id=_resolver_usuario(control.ingreso_id, db),
                plazo_objetivo=datetime.combine(control.fecha_control, time.min, tzinfo=timezone.utc),
                ventana_dias=0,
                email_enviado=False,
            )
        )
        creadas += 1
    if creadas:
        db.flush()
        record_audit(db, actor=ACTOR, action="CREATE", entity="alerta_notif", entity_id=f"control:{control.id}")
    return creadas


def resolver_alertas_control(db: Session, control_id: int) -> None:
    """Resuelve las alertas abiertas de un control que el sync va a eliminar."""
    ahora = datetime.now(timezone.utc)
    for alerta in db.scalars(
        select(AlertaNotif).where(
            AlertaNotif.caso_tipo == CASO_TIPO,
            AlertaNotif.caso_id == control_id,
            AlertaNotif.tipo.in_(TIPOS),
            AlertaNotif.estado != EstadoAlerta.RESUELTA.value,
        )
    ):
        alerta.estado = EstadoAlerta.RESUELTA.value
        alerta.resuelta_en = ahora
    db.flush()
```

`backend/app/services/salutem_sync/controles.py` — `sincronizar_control` queda así (agregar `from app.services.salutem_sync.alertas_control import alertar_control, resolver_alertas_control` a los imports):

```python
def sincronizar_control(db: Session, atencion: SalutemAtencion, ingreso: Ingreso, *, hoy: date) -> None:
    """Crea, actualiza o elimina el control del ingreso que corresponde a esta atención.

    Si la atención deja de ser control (se anuló, desapareció o no es de Médico/a) su
    control se elimina, salvo que el CEPA ya le haya registrado la RECA. Al crear o
    actualizar, alerta si el médico emitió una licencia o una receta.
    """
    control = db.scalars(
        select(ControlMedico)
        .where(ControlMedico.ingreso_id == ingreso.id, ControlMedico.salutem_cita_id == atencion.cita_id)
        .order_by(ControlMedico.id)
    ).first()
    if not es_control(atencion):
        if control is not None and control.origen == ORIGEN and control.estado_reca is None:
            resolver_alertas_control(db, control.id)
            record_audit(db, actor=ACTOR, action="DELETE", entity="control_medico", entity_id=str(control.id))
            db.delete(control)
            db.flush()
        return
    campos = _campos(db, atencion, ingreso)
    if control is None:
        control = ControlMedico(ingreso_id=ingreso.id, origen=ORIGEN, salutem_cita_id=atencion.cita_id, **campos)
        db.add(control)
        db.flush()
        record_audit(db, actor=ACTOR, action="CREATE", entity="control_medico", entity_id=str(control.id))
    elif any(getattr(control, k) != v for k, v in campos.items()):
        for k, v in campos.items():
            setattr(control, k, v)
        db.flush()
        record_audit(db, actor=ACTOR, action="UPDATE", entity="control_medico", entity_id=str(control.id))
    alertar_control(db, control, atencion.contenido, hoy)
```

`backend/app/services/salutem_sync/vinculacion.py:99` — importar `from app.services.salutem_sync.incremental import hoy_en_santiago` y cambiar la llamada:

```python
                        sincronizar_control(db, atencion, ingreso, hoy=hoy_en_santiago(ahora))
```

Si importar `incremental` desde `vinculacion` produce un import circular, definir en `vinculacion.py` `hoy = ahora.astimezone(ZoneInfo("America/Santiago")).date()` con `from zoneinfo import ZoneInfo`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"$PY/pytest" tests/salutem_sync -q`
Expected: PASS, incluidos los tests existentes de `test_controles_desde_salutem.py` y `test_vinculacion.py`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/enums_alertas.py backend/app/services/alertas.py backend/app/services/salutem_sync/alertas_control.py backend/app/services/salutem_sync/controles.py backend/app/services/salutem_sync/vinculacion.py backend/tests/salutem_sync/test_alertas_control.py
git commit -m "feat(alertas): alertar licencia y receta emitidas en los controles de SALUTEM

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 3: Cliente SALUTEM — biblioteca de archivos (solo lectura)

**Files:**
- Modify: `backend/app/integrations/salutem/models.py` (DTOs `ArchivoSalutem`, `ContenidoArchivo`)
- Modify: `backend/app/integrations/salutem/protocol.py` (dos métodos)
- Modify: `backend/app/integrations/salutem/client.py` (stub y HTTP)
- Modify: `backend/tests/salutem_falso.py` (biblioteca en memoria)
- Test: `backend/tests/test_salutem_http_client.py` (casos nuevos al final)

**Interfaces:**
- Produces:
  - `ArchivoSalutem(archivo_id: int, persona_id: int, nombre: str, tipo: str | None, fecha_creacion: datetime | None, crudo: dict)` con `ArchivoSalutem.desde_api(d: dict, persona_id: int)`.
  - `ContenidoArchivo(nombre: str, media_type: str, datos: bytes)` con `ContenidoArchivo.desde_api(d: dict) -> ContenidoArchivo | None` (None si `archivo_base64` viene vacío).
  - `SalutemClientProtocol.listar_archivos(salutem_id: int) -> list[ArchivoSalutem]` y `obtener_archivo(salutem_id: int, archivo_id: int) -> ContenidoArchivo | None`.
  - `SalutemFalso.agregar_archivo(archivo_id, persona_id, nombre="doc.pdf", creado="15-10-2026 16:29", datos=b"%PDF-1.4 prueba", tipo="documento")`, `SalutemFalso.personas_archivos_caidas: set[int]`.

- [ ] **Step 1: Write the failing test**

Al final de `backend/tests/test_salutem_http_client.py`:

```python
# ── Biblioteca de archivos (/personas-archivos) ───────────────────────────────

import base64  # noqa: E402
from datetime import datetime  # noqa: E402

PDF = b"%PDF-1.6 contenido de prueba"


def test_listar_archivos_pide_la_biblioteca_de_la_persona():
    visto = {}

    def handler(request):
        visto["ruta"] = request.url.path
        visto["cuerpo"] = json.loads(request.content)
        return _ok([
            {"id": 1368688, "nombre": "boletaPPL ripley.pdf", "nombreOriginal": "boletaPPL ripley.pdf",
             "fechaCreacion": "15-10-2026 16:29", "tipo": "documento", "descripcion": ""},
        ])

    [archivo] = _cliente(handler).listar_archivos(1180505)

    assert visto["ruta"].endswith("/96/personas-archivos")
    assert visto["cuerpo"] == {"persona_id": "1180505"}
    assert (archivo.archivo_id, archivo.persona_id, archivo.nombre, archivo.tipo) == (
        1368688, 1180505, "boletaPPL ripley.pdf", "documento")
    assert archivo.fecha_creacion == datetime(2026, 10, 15, 16, 29)


def test_una_fecha_de_creacion_ilegible_queda_nula():
    handler = lambda request: _ok([{"id": 1, "nombre": "x.pdf", "fechaCreacion": "ayer", "tipo": "documento"}])  # noqa: E731
    [archivo] = _cliente(handler).listar_archivos(1)
    assert archivo.fecha_creacion is None


def test_obtener_archivo_decodifica_el_base64_y_detecta_el_tipo():
    visto = {}

    def handler(request):
        visto["cuerpo"] = json.loads(request.content)
        return _ok({"id": 7, "nombre": "lm.pdf", "nombreOriginal": "LICENCIA.pdf",
                    "archivo_base64": base64.b64encode(PDF).decode()})

    contenido = _cliente(handler).obtener_archivo(1180505, 7)

    assert visto["cuerpo"] == {"persona_id": "1180505", "archivo_id": "7"}
    assert (contenido.nombre, contenido.media_type, contenido.datos) == ("LICENCIA.pdf", "application/pdf", PDF)


def test_un_base64_vacio_es_un_archivo_sin_contenido():
    handler = lambda request: _ok({"id": 7, "nombre": "x.pdf", "archivo_base64": ""})  # noqa: E731
    assert _cliente(handler).obtener_archivo(1, 7) is None


def test_una_foto_jpeg_se_reconoce():
    jpeg = b"\xff\xd8\xff\xe0 foto"
    handler = lambda request: _ok({"id": 8, "nombre": "r.jpg", "archivo_base64": base64.b64encode(jpeg).decode()})  # noqa: E731
    assert _cliente(handler).obtener_archivo(1, 8).media_type == "image/jpeg"


def test_el_cliente_sigue_cumpliendo_el_protocolo_con_la_biblioteca():
    assert isinstance(_cliente(lambda r: _ok([])), SalutemClientProtocol)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"$PY/pytest" tests/test_salutem_http_client.py -q`
Expected: FAIL con `AttributeError: 'SalutemHttpClient' object has no attribute 'listar_archivos'`

- [ ] **Step 3: Write minimal implementation**

En `backend/app/integrations/salutem/models.py` (agregar `import base64` y `from datetime import date, datetime`):

```python
def _fecha_archivo(valor: Any) -> datetime | None:
    """SALUTEM entrega `fechaCreacion` como "DD-MM-AAAA HH:MM", hora de Chile."""
    if not isinstance(valor, str):
        return None
    try:
        return datetime.strptime(valor.strip()[:16], "%d-%m-%Y %H:%M")
    except ValueError:
        return None


_FIRMAS = (
    (b"%PDF", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG", "image/png"),
    (b"GIF8", "image/gif"),
)


def _media_type(datos: bytes) -> str:
    for firma, tipo in _FIRMAS:
        if datos.startswith(firma):
            return tipo
    if datos[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1"):
        return "image/heic"
    return "application/octet-stream"


class ArchivoSalutem(BaseModel):
    """Un archivo de la biblioteca de la persona. El listado no trae carpeta ni cita."""

    model_config = ConfigDict(frozen=True)

    archivo_id: int
    persona_id: int
    nombre: str
    tipo: str | None = None
    fecha_creacion: datetime | None = None
    crudo: dict[str, Any] = {}

    @classmethod
    def desde_api(cls, d: dict[str, Any], persona_id: int) -> "ArchivoSalutem":
        nombre = str(d.get("nombreOriginal") or d.get("nombre") or "")
        return cls(
            archivo_id=int(d["id"]),
            persona_id=persona_id,
            nombre=nombre[:255],
            tipo=d.get("tipo"),
            fecha_creacion=_fecha_archivo(d.get("fechaCreacion")),
            crudo=d,
        )


class ContenidoArchivo(BaseModel):
    """El archivo descargado. No se persiste: se entrega al navegador y se descarta."""

    model_config = ConfigDict(frozen=True)

    nombre: str
    media_type: str
    datos: bytes

    @classmethod
    def desde_api(cls, d: dict[str, Any]) -> "ContenidoArchivo | None":
        # La copia de QA no conserva los binarios antiguos: llega el registro con base64 vacío.
        crudo = d.get("archivo_base64") or ""
        if not crudo.strip():
            return None
        datos = base64.b64decode(crudo)
        return cls(
            nombre=str(d.get("nombreOriginal") or d.get("nombre") or "archivo"),
            media_type=_media_type(datos),
            datos=datos,
        )
```

En `protocol.py`, importar los dos DTOs y agregar a `SalutemClientProtocol`:

```python
    def listar_archivos(self, salutem_id: int) -> list[ArchivoSalutem]:
        """Lista la biblioteca de la persona (sin contenido). Lista vacía si no hay."""
        ...

    def obtener_archivo(self, salutem_id: int, archivo_id: int) -> ContenidoArchivo | None:
        """Trae un archivo con su contenido. None si no existe o llega sin contenido."""
        ...
```

En `client.py`, importar los DTOs; en `SalutemStubClient`:

```python
    def listar_archivos(self, salutem_id: int) -> list[ArchivoSalutem]:  # noqa: ARG002
        return []

    def obtener_archivo(self, salutem_id: int, archivo_id: int) -> ContenidoArchivo | None:  # noqa: ARG002
        return None
```

y en `SalutemHttpClient`:

```python
    def listar_archivos(self, salutem_id: int) -> list[ArchivoSalutem]:
        r = self._get("personas-archivos", {"persona_id": str(salutem_id)})
        return [ArchivoSalutem.desde_api(x, salutem_id) for x in (r or [])]

    def obtener_archivo(self, salutem_id: int, archivo_id: int) -> ContenidoArchivo | None:
        r = self._get("personas-archivos", {"persona_id": str(salutem_id), "archivo_id": str(archivo_id)})
        return ContenidoArchivo.desde_api(r) if r else None
```

En `backend/tests/salutem_falso.py` (importar `base64`, `ArchivoSalutem`, `ContenidoArchivo`): en `__init__` agregar

```python
        self.archivos: dict[int, dict] = {}
        self.personas_archivos_caidas: set[int] = set()
```

en "Carga de datos":

```python
    def agregar_archivo(
        self,
        archivo_id: int,
        persona_id: int,
        nombre: str = "doc.pdf",
        creado: str = "15-10-2026 16:29",
        datos: bytes = b"%PDF-1.4 prueba",
        tipo: str = "documento",
    ) -> None:
        self.archivos[archivo_id] = {
            "id": archivo_id, "personaId": persona_id, "nombre": nombre, "nombreOriginal": nombre,
            "fechaCreacion": creado, "tipo": tipo, "descripcion": "",
            "archivo_base64": base64.b64encode(datos).decode(),
        }
```

y en "Protocolo":

```python
    def listar_archivos(self, salutem_id: int) -> list[ArchivoSalutem]:
        self._registrar("listar_archivos", salutem_id)
        if salutem_id in self.personas_archivos_caidas:
            raise SalutemUnavailableError("SALUTEM devolvió un cuerpo ilegible (HTTP 504)")
        return [
            ArchivoSalutem.desde_api(a, salutem_id)
            for a in self.archivos.values()
            if a["personaId"] == salutem_id
        ]

    def obtener_archivo(self, salutem_id: int, archivo_id: int) -> ContenidoArchivo | None:
        self._registrar("obtener_archivo", salutem_id, archivo_id)
        a = self.archivos.get(archivo_id)
        if a is None or a["personaId"] != salutem_id:
            return None
        return ContenidoArchivo.desde_api(a)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `"$PY/pytest" tests/test_salutem_http_client.py tests/test_salutem_no_escribe.py tests/salutem_sync -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/salutem/models.py backend/app/integrations/salutem/protocol.py backend/app/integrations/salutem/client.py backend/tests/salutem_falso.py backend/tests/test_salutem_http_client.py
git commit -m "feat(salutem): leer la biblioteca de archivos de la persona (solo lectura)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 4: Copia de la biblioteca en el ciclo `caliente`

**Files:**
- Modify: `backend/app/models/salutem_copia.py` (modelo `SalutemArchivo`)
- Create: `backend/migrations/versions/1320_salutem_archivo.py`
- Create: `backend/app/services/salutem_sync/archivos.py`
- Modify: `backend/app/services/salutem_sync/orquestador.py:103-112` (llamada tras la vinculación en `caliente`)
- Test: `backend/tests/salutem_sync/test_archivos.py`

**Interfaces:**
- Consumes: `listar_archivos` (Tarea 3), `SalutemFalso.agregar_archivo`.
- Produces: `SalutemArchivo` (tabla `salutem_archivo`: `archivo_id` PK, `persona_id`, `nombre`, `tipo`, `fecha_creacion`, `visto_ultima_vez`, `desaparecido_en`); `refrescar_archivos(db, cliente, ritmo, ahora) -> ResultadoArchivos(personas: int, errores: list[str])`; `DIAS_RECIENTES = 7`.

- [ ] **Step 1: Write the failing test**

`backend/tests/salutem_sync/test_archivos.py`:

```python
"""Copia de la biblioteca de SALUTEM para las personas con controles recientes."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.integrations.salutem.errors import SalutemAuthError
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion
from app.services.salutem_sync.archivos import refrescar_archivos
from tests.salutem_sync.conftest import AHORA

PERSONA = 1180505


def _control(db, cita_id=16625887, fecha=date(2026, 9, 15), persona=PERSONA) -> ControlMedico:
    paciente = Paciente(rut=f"39{cita_id}", nombre="P", sexo="M", edad=50, region="Maule")
    db.add(paciente)
    db.flush()
    ingreso = Ingreso(paciente_id=paciente.id, folio=f"F-{cita_id}", folio_manual=True,
                      fecha_ingreso=date(2026, 8, 1), tipo_derivacion="DIEP", tipo_ingreso="convenio",
                      modelo_tratamiento="ambulatorio", diagnostico="prueba", estado="activo")
    db.add(ingreso)
    db.flush()
    db.add(SalutemAtencion(cita_id=cita_id, persona_id=persona, fecha_cita=fecha, contenido={},
                           hash_contenido="x", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
                           cambiado_en=AHORA))
    control = ControlMedico(ingreso_id=ingreso.id, origen="SALUTEM", salutem_cita_id=cita_id,
                            fecha_control=fecha, semana_control=7, medico_tratante="DRA",
                            region_derivacion="Maule")
    db.add(control)
    db.flush()
    return control


def _archivos(db) -> list[SalutemArchivo]:
    return list(db.scalars(select(SalutemArchivo).order_by(SalutemArchivo.archivo_id)))


def test_guarda_la_metadata_de_los_archivos_de_personas_con_control_reciente(db_session, salutem, ritmo):
    _control(db_session)
    salutem.agregar_archivo(1368688, PERSONA, nombre="boletaPPL ripley.pdf", creado="15-09-2026 16:29")

    r = refrescar_archivos(db_session, salutem, ritmo, AHORA)

    [a] = _archivos(db_session)
    assert (a.archivo_id, a.persona_id, a.nombre, a.tipo) == (1368688, PERSONA, "boletaPPL ripley.pdf", "documento")
    assert a.fecha_creacion == datetime(2026, 9, 15, 16, 29)
    assert a.desaparecido_en is None
    assert (r.personas, r.errores) == (1, [])
    assert not hasattr(a, "contenido")


def test_no_lista_personas_sin_control_reciente(db_session, salutem, ritmo):
    _control(db_session, fecha=date(2026, 8, 1))  # 46 días antes de AHORA
    salutem.agregar_archivo(1, PERSONA)

    refrescar_archivos(db_session, salutem, ritmo, AHORA)

    assert salutem.llamadas_a("listar_archivos") == []
    assert _archivos(db_session) == []


def test_un_archivo_que_ya_no_esta_queda_desaparecido_y_puede_volver(db_session, salutem, ritmo):
    _control(db_session)
    salutem.agregar_archivo(1, PERSONA)
    refrescar_archivos(db_session, salutem, ritmo, AHORA)
    del salutem.archivos[1]

    refrescar_archivos(db_session, salutem, ritmo, AHORA + timedelta(minutes=5))
    assert _archivos(db_session)[0].desaparecido_en is not None

    salutem.agregar_archivo(1, PERSONA)
    refrescar_archivos(db_session, salutem, ritmo, AHORA + timedelta(minutes=10))
    assert _archivos(db_session)[0].desaparecido_en is None


def test_salutem_caido_en_una_persona_no_detiene_a_las_demas(db_session, salutem, ritmo):
    _control(db_session, cita_id=1, persona=PERSONA)
    _control(db_session, cita_id=2, persona=PERSONA + 1)
    salutem.personas_archivos_caidas.add(PERSONA)
    salutem.agregar_archivo(9, PERSONA + 1)

    r = refrescar_archivos(db_session, salutem, ritmo, AHORA)

    assert [a.archivo_id for a in _archivos(db_session)] == [9]
    assert r.personas == 1
    assert len(r.errores) == 1 and str(PERSONA) in r.errores[0]


def test_una_credencial_rechazada_aborta(db_session, salutem, ritmo):
    _control(db_session)
    salutem.credencial_rechazada = True

    with pytest.raises(SalutemAuthError):
        refrescar_archivos(db_session, salutem, ritmo, AHORA)


def test_una_fecha_ilegible_se_guarda_nula(db_session, salutem, ritmo):
    _control(db_session)
    salutem.agregar_archivo(3, PERSONA, creado="ayer")

    refrescar_archivos(db_session, salutem, ritmo, AHORA)

    assert _archivos(db_session)[0].fecha_creacion is None
```

Antes de correrlo, confirmar en `backend/app/models/control_medico.py` las columnas obligatorias de `ControlMedico` y completar el constructor de `_control` si falta alguna.

Agregar en `backend/tests/salutem_sync/test_orquestador.py`:

```python
def test_caliente_copia_la_biblioteca_despues_de_vincular(db_session, salutem, ritmo, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "app.services.salutem_sync.orquestador.refrescar_archivos",
        lambda db, cliente, ritmo, ahora: llamadas.append(ahora) or ResultadoArchivos(),
    )
    assert _correr(db_session, salutem, ritmo, modo="caliente") == 0
    assert llamadas == [AHORA]


def test_tibia_no_copia_la_biblioteca(db_session, salutem, ritmo, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "app.services.salutem_sync.orquestador.refrescar_archivos",
        lambda *a: llamadas.append(a) or ResultadoArchivos(),
    )
    assert _correr(db_session, salutem, ritmo, modo="tibia") == 0
    assert llamadas == []
```

con `from app.services.salutem_sync.archivos import ResultadoArchivos` en sus imports.

- [ ] **Step 2: Run test to verify it fails**

Run: `"$PY/pytest" tests/salutem_sync/test_archivos.py tests/salutem_sync/test_orquestador.py -q`
Expected: FAIL con `ImportError: cannot import name 'SalutemArchivo'`

- [ ] **Step 3: Write minimal implementation**

En `backend/app/models/salutem_copia.py` (sin `_RegistroCopia`: no se guarda contenido):

```python
class SalutemArchivo(Base):
    """Metadata de un archivo de la biblioteca de SALUTEM. El contenido no se copia."""

    __tablename__ = "salutem_archivo"

    archivo_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    # Sin FK: como salutem_cita, puede llegar antes que su persona.
    persona_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Hora de Chile, sin zona (como salutem_cita.fecha_creacion).
    fecha_creacion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    visto_ultima_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    desaparecido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

`backend/migrations/versions/1320_salutem_archivo.py`:

```python
"""salutem_archivo: metadata de la biblioteca de archivos de SALUTEM

Solo id, nombre, tipo y fecha de cada archivo; el contenido se pide a SALUTEM al abrirlo.

Revision ID: 1320
Revises: 1310
"""

import sqlalchemy as sa
from alembic import op

revision = "1320"
down_revision = "1310"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "salutem_archivo",
        sa.Column("archivo_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("visto_ultima_vez", sa.DateTime(timezone=True), nullable=False),
        sa.Column("desaparecido_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("archivo_id"),
    )
    op.create_index("ix_salutem_archivo_persona_id", "salutem_archivo", ["persona_id"])
    op.create_index("ix_salutem_archivo_fecha_creacion", "salutem_archivo", ["fecha_creacion"])


def downgrade() -> None:
    op.drop_index("ix_salutem_archivo_fecha_creacion", table_name="salutem_archivo")
    op.drop_index("ix_salutem_archivo_persona_id", table_name="salutem_archivo")
    op.drop_table("salutem_archivo")
```

Verificar que los nombres de índice coincidan con los que genera el modelo (`index=True` produce `ix_<tabla>_<columna>`): si `tests/salutem_sync/test_migracion.py` compara modelo y migración, debe seguir verde.

`backend/app/services/salutem_sync/archivos.py`:

```python
"""Copia de la biblioteca de archivos de SALUTEM (solo metadata).

En cada ciclo `caliente` se lista la biblioteca de las personas con un control de los
últimos DIAS_RECIENTES días: el médico suele subir la licencia o la receta al final del
día o días después, así que no basta con listarla al crear el control. Lo que deja de
aparecer queda con `desaparecido_en`; nunca se borra una fila.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.salutem.errors import SalutemAuthError, SalutemError
from app.integrations.salutem.models import ArchivoSalutem
from app.integrations.salutem.protocol import SalutemClientProtocol
from app.models.control_medico import ControlMedico
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion
from app.services.salutem_sync.barrido import describir_error
from app.services.salutem_sync.incremental import hoy_en_santiago
from app.services.salutem_sync.ritmo import Ritmo

DIAS_RECIENTES = 7


@dataclass
class ResultadoArchivos:
    personas: int = 0
    errores: list[str] = field(default_factory=list)


def _personas_con_control_reciente(db: Session, ahora: datetime) -> list[int]:
    desde = hoy_en_santiago(ahora) - timedelta(days=DIAS_RECIENTES)
    return list(
        db.scalars(
            select(SalutemAtencion.persona_id)
            .join(ControlMedico, ControlMedico.salutem_cita_id == SalutemAtencion.cita_id)
            .where(ControlMedico.fecha_control >= desde)
            .distinct()
            .order_by(SalutemAtencion.persona_id)
        )
    )


def guardar_archivos(db: Session, persona_id: int, archivos: list[ArchivoSalutem], ahora: datetime) -> None:
    vistos = {a.archivo_id for a in archivos}
    for a in archivos:
        fila = db.get(SalutemArchivo, a.archivo_id)
        if fila is None:
            fila = SalutemArchivo(archivo_id=a.archivo_id, persona_id=persona_id)
            db.add(fila)
        fila.nombre, fila.tipo, fila.fecha_creacion = a.nombre, a.tipo, a.fecha_creacion
        fila.visto_ultima_vez, fila.desaparecido_en = ahora, None
    for fila in db.scalars(
        select(SalutemArchivo).where(
            SalutemArchivo.persona_id == persona_id, SalutemArchivo.desaparecido_en.is_(None)
        )
    ):
        if fila.archivo_id not in vistos:
            fila.desaparecido_en = ahora
    db.flush()


def refrescar_archivos(
    db: Session, cliente: SalutemClientProtocol, ritmo: Ritmo, ahora: datetime
) -> ResultadoArchivos:
    """Lista la biblioteca de cada persona con control reciente y guarda su metadata.

    Una persona que falla se registra y se salta: la vinculación de este ciclo ya está
    hecha y no se pierde. Una credencial rechazada aborta, como en el resto del sync.
    """
    r = ResultadoArchivos()
    for persona_id in _personas_con_control_reciente(db, ahora):
        try:
            archivos = ritmo.llamar(cliente.listar_archivos, persona_id)
        except SalutemAuthError:
            raise
        except SalutemError as e:
            r.errores.append(f"archivos de la persona {persona_id}: {describir_error(e)}")
            continue
        guardar_archivos(db, persona_id, archivos, ahora)
        r.personas += 1
    return r
```

En `backend/app/services/salutem_sync/orquestador.py`: importar `from app.services.salutem_sync.archivos import refrescar_archivos` y, en `correr`, justo después de `errores = errores + vinculacion.errores`:

```python
        if modo == "caliente":
            archivos = refrescar_archivos(db, cliente, ritmo, ahora())
            errores = errores + archivos.errores
            log.info("Biblioteca SALUTEM: %d personas revisadas", archivos.personas)
```

Si `SalutemFalso.credencial_rechazada` hace que `_registrar` levante antes de llegar a `listar_archivos`, el test de credencial ya lo cubre: `_registrar` se llama primero en el método falso.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"$PY/pytest" tests/salutem_sync -q`
Expected: PASS (incluido `test_migracion.py`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/salutem_copia.py backend/migrations/versions/1320_salutem_archivo.py backend/app/services/salutem_sync/archivos.py backend/app/services/salutem_sync/orquestador.py backend/tests/salutem_sync/test_archivos.py backend/tests/salutem_sync/test_orquestador.py
git commit -m "feat(salutem-sync): copiar la metadata de la biblioteca en el ciclo caliente

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 5: API — documentos de un control y su contenido

**Files:**
- Create: `backend/app/services/archivos_control.py`
- Modify: `backend/app/schemas/control_medico.py` (schema `ArchivoControlRead`)
- Modify: `backend/app/routers/controles_medicos.py` (dos endpoints)
- Test: `backend/tests/test_archivos_control_api.py`

**Interfaces:**
- Consumes: `SalutemArchivo` (Tarea 4), `get_salutem_client().obtener_archivo` (Tarea 3).
- Produces:
  - `archivos_de_control(db, control) -> list[SalutemArchivo]`, `persona_de_control(db, control) -> int | None`, `VENTANA_DIAS = 7`.
  - `GET /api/v1/controles-medicos/{control_id}/archivos` → `list[ArchivoControlRead]` con `{archivo_id: int, nombre: str, tipo: str | null, fecha_creacion: datetime | null}`.
  - `GET /api/v1/controles-medicos/{control_id}/archivos/{archivo_id}/contenido` → bytes con `Content-Type` del archivo y `Content-Disposition: inline`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_archivos_control_api.py`:

```python
"""Documentos de la biblioteca de SALUTEM unidos a un control, y su descarga bajo demanda."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.audit.models import AuditLog
from app.integrations.salutem.errors import SalutemUnavailableError
from app.integrations.salutem.models import ContenidoArchivo
from app.models.control_medico import ControlMedico
from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion

AHORA = datetime(2026, 10, 15, 20, 0, tzinfo=timezone.utc)
PERSONA = 1180505


def _ingreso(db) -> Ingreso:
    p = Paciente(rut="390001180", nombre="Humberto Escobar", sexo="M", edad=50, region="Maule")
    db.add(p)
    db.flush()
    i = Ingreso(paciente_id=p.id, folio="F-2026-1180", folio_manual=True, fecha_ingreso=date(2026, 9, 1),
                tipo_derivacion="DIEP", tipo_ingreso="convenio", modelo_tratamiento="ambulatorio",
                diagnostico="prueba", estado="activo")
    db.add(i)
    db.flush()
    return i


def _control(db, ingreso, cita_id, fecha, persona=PERSONA) -> ControlMedico:
    db.add(SalutemAtencion(cita_id=cita_id, persona_id=persona, fecha_cita=fecha, contenido={},
                           hash_contenido="x", visto_primera_vez=AHORA, visto_ultima_vez=AHORA,
                           cambiado_en=AHORA))
    c = ControlMedico(ingreso_id=ingreso.id, origen="SALUTEM", salutem_cita_id=cita_id, fecha_control=fecha,
                      semana_control=7, medico_tratante="DRA", region_derivacion="Maule")
    db.add(c)
    db.flush()
    return c


def _archivo(db, archivo_id, creado, persona=PERSONA, desaparecido=None):
    db.add(SalutemArchivo(archivo_id=archivo_id, persona_id=persona, nombre=f"doc{archivo_id}.pdf",
                          tipo="documento", fecha_creacion=creado, visto_ultima_vez=AHORA,
                          desaparecido_en=desaparecido))
    db.flush()


@pytest.fixture
def escenario(db_session):
    ingreso = _ingreso(db_session)
    c1 = _control(db_session, ingreso, 16625887, date(2026, 10, 15))
    _control(db_session, ingreso, 16625990, date(2026, 10, 18))       # el control siguiente
    _archivo(db_session, 1, datetime(2026, 10, 15, 16, 29))            # mismo día → c1
    _archivo(db_session, 2, datetime(2026, 10, 17, 9, 0))              # antes del siguiente → c1
    _archivo(db_session, 3, datetime(2026, 10, 18, 9, 0))              # día del siguiente → no
    _archivo(db_session, 4, datetime(2026, 10, 14, 23, 59))            # día anterior → no
    _archivo(db_session, 5, datetime(2026, 10, 15, 17, 0), persona=999)  # otra persona → no
    _archivo(db_session, 6, datetime(2026, 10, 15, 18, 0), desaparecido=AHORA)  # borrado → no
    _archivo(db_session, 7, None)                                      # fecha ilegible → no
    return c1


def test_lista_los_archivos_del_dia_hasta_el_control_siguiente(as_admin, escenario):
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos")
    assert r.status_code == 200, r.text
    assert [a["archivo_id"] for a in r.json()] == [1, 2]
    assert r.json()[0] == {"archivo_id": 1, "nombre": "doc1.pdf", "tipo": "documento",
                           "fecha_creacion": "2026-10-15T16:29:00"}


def test_la_ventana_tiene_un_tope_de_siete_dias(as_admin, db_session):
    ingreso = _ingreso(db_session)
    c = _control(db_session, ingreso, 500, date(2026, 10, 1))
    _archivo(db_session, 10, datetime(2026, 10, 7, 23, 0))
    _archivo(db_session, 11, datetime(2026, 10, 8, 0, 1))
    r = as_admin.get(f"/api/v1/controles-medicos/{c.id}/archivos")
    assert [a["archivo_id"] for a in r.json()] == [10]


def test_un_control_sin_atencion_de_salutem_no_tiene_archivos(as_admin, db_session):
    ingreso = _ingreso(db_session)
    c = ControlMedico(ingreso_id=ingreso.id, origen="CEPA", fecha_control=date(2026, 10, 15),
                      semana_control=7, medico_tratante="DRA", region_derivacion="Maule")
    db_session.add(c)
    db_session.flush()
    assert as_admin.get(f"/api/v1/controles-medicos/{c.id}/archivos").json() == []


def test_el_contenido_se_pide_a_salutem_y_se_audita(as_admin, db_session, escenario, monkeypatch):
    pedidos = []

    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            pedidos.append((salutem_id, archivo_id))
            return ContenidoArchivo(nombre="LICENCIA 15 octubre.pdf", media_type="application/pdf", datos=b"%PDF-1.6")

    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client", lambda: Cliente())

    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/1/contenido")

    assert r.status_code == 200
    assert r.content == b"%PDF-1.6"
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith("inline;")
    assert pedidos == [(PERSONA, 1)]
    auditoria = db_session.scalars(select(AuditLog).where(AuditLog.entity == "salutem_archivo")).all()
    assert [(a.action, a.entity_id) for a in auditoria] == [("READ", "1")]


@pytest.mark.parametrize("archivo_id", [3, 4, 5, 6, 999])
def test_un_archivo_que_no_es_del_control_no_se_descarga(as_admin, escenario, monkeypatch, archivo_id):
    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client",
                        lambda: pytest.fail("no debe llamar a SALUTEM"))
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/{archivo_id}/contenido")
    assert r.status_code == 404


def test_sin_contenido_en_salutem_responde_404(as_admin, escenario, monkeypatch):
    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            return None

    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client", lambda: Cliente())
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/1/contenido")
    assert r.status_code == 404
    assert r.json()["detail"] == "SALUTEM no entregó el contenido del archivo"


def test_salutem_caido_responde_502(as_admin, escenario, monkeypatch):
    class Cliente:
        def obtener_archivo(self, salutem_id, archivo_id):
            raise SalutemUnavailableError("HTTP 504")

    monkeypatch.setattr("app.routers.controles_medicos.get_salutem_client", lambda: Cliente())
    r = as_admin.get(f"/api/v1/controles-medicos/{escenario.id}/archivos/1/contenido")
    assert r.status_code == 502


def test_el_auditor_puede_leer(as_auditor, escenario):
    assert as_auditor.get(f"/api/v1/controles-medicos/{escenario.id}/archivos").status_code == 200


def test_sin_sesion_no_hay_acceso(client, escenario):
    assert client.get(f"/api/v1/controles-medicos/{escenario.id}/archivos").status_code == 401
```

Antes de correrlo: confirmar el módulo del modelo de auditoría (`grep -rn "class AuditLog" backend/app`) y ajustar el import; si el código sin sesión es 403 en este proyecto, usar el que devuelven los demás tests de `test_control_medico_api.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `"$PY/pytest" tests/test_archivos_control_api.py -q`
Expected: FAIL con 404 en las rutas `/archivos` (no existen).

- [ ] **Step 3: Write minimal implementation**

`backend/app/services/archivos_control.py`:

```python
"""Documentos de la biblioteca de SALUTEM que acompañan a un control.

La API de SALUTEM no une el archivo con la cita ni dice si es licencia o receta: se
unen por fecha. Un control lleva los archivos de la persona creados desde el día del
control hasta el día anterior al control siguiente del ingreso, con un tope de
VENTANA_DIAS. No se clasifican: la encargada los abre y decide.
"""

from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.control_medico import ControlMedico
from app.models.salutem_copia import SalutemArchivo, SalutemAtencion

VENTANA_DIAS = 7


def persona_de_control(db: Session, control: ControlMedico) -> int | None:
    if control.salutem_cita_id is None:
        return None
    atencion = db.get(SalutemAtencion, control.salutem_cita_id)
    return atencion.persona_id if atencion else None


def archivos_de_control(db: Session, control: ControlMedico) -> list[SalutemArchivo]:
    persona_id = persona_de_control(db, control)
    if persona_id is None:
        return []
    fin = control.fecha_control + timedelta(days=VENTANA_DIAS)
    siguiente = db.scalar(
        select(func.min(ControlMedico.fecha_control)).where(
            ControlMedico.ingreso_id == control.ingreso_id,
            ControlMedico.fecha_control > control.fecha_control,
        )
    )
    if siguiente is not None and siguiente < fin:
        fin = siguiente
    return list(
        db.scalars(
            select(SalutemArchivo)
            .where(
                SalutemArchivo.persona_id == persona_id,
                SalutemArchivo.desaparecido_en.is_(None),
                SalutemArchivo.fecha_creacion >= datetime.combine(control.fecha_control, time.min),
                SalutemArchivo.fecha_creacion < datetime.combine(fin, time.min),
            )
            .order_by(SalutemArchivo.fecha_creacion, SalutemArchivo.archivo_id)
        )
    )
```

En `backend/app/schemas/control_medico.py`:

```python
class ArchivoControlRead(BaseModel):
    """Un documento de la biblioteca de SALUTEM unido al control por fecha."""

    model_config = ConfigDict(from_attributes=True)

    archivo_id: int
    nombre: str
    tipo: str | None
    fecha_creacion: datetime | None
```

(importar `datetime` y `ConfigDict` si el módulo no los tiene).

En `backend/app/routers/controles_medicos.py` (agregar al docstring las dos rutas e importar `from urllib.parse import quote`, `from fastapi import HTTPException, Response`, `from app.integrations.salutem.client import get_salutem_client`, `from app.integrations.salutem.errors import SalutemError`, `from app.schemas.control_medico import ArchivoControlRead`, `from app.services.archivos_control import archivos_de_control, persona_de_control`):

```python
# ── Documentos de la biblioteca de SALUTEM ───────────────────────────────────

@router.get(
    "/{control_id}/archivos",
    response_model=list[ArchivoControlRead],
    dependencies=[Depends(_reader)],
)
def listar_archivos(control_id: int, db: Session = Depends(get_db)) -> list[ArchivoControlRead]:
    return archivos_de_control(db, _get_control_o_404(db, control_id))


@router.get(
    "/{control_id}/archivos/{archivo_id}/contenido",
    response_class=Response,
    dependencies=[Depends(_reader)],
)
def contenido_archivo(
    control_id: int,
    archivo_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """Pide el archivo a SALUTEM y lo entrega sin guardarlo (ni en BD ni en disco)."""
    control = _get_control_o_404(db, control_id)
    if archivo_id not in {a.archivo_id for a in archivos_de_control(db, control)}:
        raise HTTPException(status_code=404, detail="El archivo no pertenece a este control")
    try:
        contenido = get_salutem_client().obtener_archivo(persona_de_control(db, control), archivo_id)
    except SalutemError as e:
        raise HTTPException(status_code=502, detail="SALUTEM no respondió") from e
    if contenido is None:
        raise HTTPException(status_code=404, detail="SALUTEM no entregó el contenido del archivo")
    record_audit(db, actor=current_user.username, action="READ", entity="salutem_archivo", entity_id=str(archivo_id))
    db.commit()
    return Response(
        content=contenido.datos,
        media_type=contenido.media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(contenido.nombre)}"},
    )
```

Confirmar que `_get_control_o_404(db, control_id)` tiene esa firma (está en `app/services/control_medico.py`); si recibe otros argumentos, adaptarse a ella.

- [ ] **Step 4: Run tests to verify they pass**

Run: `"$PY/pytest" tests/test_archivos_control_api.py tests/test_control_medico_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/archivos_control.py backend/app/schemas/control_medico.py backend/app/routers/controles_medicos.py backend/tests/test_archivos_control_api.py
git commit -m "feat(controles): documentos de SALUTEM del control y descarga bajo demanda

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 6: Frontend — tipos de la API y documentos en el detalle del control

**Files:**
- Modify: `frontend/src/types/api.ts` (regenerado)
- Modify: `frontend/src/features/controles/api.ts` (dos funciones)
- Modify: `frontend/src/features/controles/hooks.ts` (un hook)
- Create: `frontend/src/features/controles/DocumentosSalutem.tsx`
- Modify: `frontend/src/features/controles/ControlesPage.tsx:209-228` (sección en el detalle)
- Test: `frontend/src/features/controles/DocumentosSalutem.test.tsx`

**Interfaces:**
- Consumes: los dos endpoints de la Tarea 5.
- Produces: `type ArchivoControlRead`; `archivosDeControl(controlId: number): Promise<ArchivoControlRead[]>`; `abrirArchivoDeControl(controlId: number, archivoId: number): Promise<void>`; `useArchivosDeControl(controlId: number, habilitado?: boolean)`; componente `DocumentosSalutem({ controlId, tieneLicencia }: { controlId: number; tieneLicencia: boolean })`.

- [ ] **Step 1: Regenerar los tipos de la API**

```bash
cd backend && "$PY/python" -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > /tmp/cepa-openapi.json
cd ../frontend && npx openapi-typescript /tmp/cepa-openapi.json -o src/types/api.ts
git diff --stat src/types/api.ts
```

Expected: el diff agrega `ArchivoControlRead`, las dos rutas `/archivos` y los dos valores nuevos de `TipoAlerta`. Si aparecen cambios ajenos a esta feature, revisarlos antes de seguir (puede haber tipos desactualizados de antes).

- [ ] **Step 2: Write the failing test**

`frontend/src/features/controles/DocumentosSalutem.test.tsx`:

```tsx
/**
 * Documentos de la biblioteca de SALUTEM unidos a un control.
 *
 * Covers:
 *  1. Lista nombre y fecha de cada documento.
 *  2. "Ver" pide el contenido con la sesión y lo abre en una pestaña nueva.
 *  3. Sin documentos y con licencia: avisa que no hay documentos en la biblioteca.
 *  4. Si SALUTEM no entrega el contenido, muestra el error.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { server } from "@/test/msw/server";
import { DocumentosSalutem } from "./DocumentosSalutem";

const BASE = import.meta.env.VITE_API_BASE_URL;

function renderizar(props: { controlId: number; tieneLicencia: boolean }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Toaster />
      <DocumentosSalutem {...props} />
    </QueryClientProvider>,
  );
}

describe("DocumentosSalutem", () => {
  const abrir = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("open", abrir);
    URL.createObjectURL = vi.fn(() => "blob:documento");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    abrir.mockReset();
  });

  it("lista los documentos del control", async () => {
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([
          { archivo_id: 1, nombre: "LICENCIA 15 oct.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" },
        ]),
      ),
    );
    renderizar({ controlId: 5, tieneLicencia: true });
    expect(await screen.findByText("LICENCIA 15 oct.pdf")).toBeInTheDocument();
    expect(screen.getByText(/15-10-2026|15\/10\/2026/)).toBeInTheDocument();
  });

  it("Ver abre el documento en una pestaña nueva", async () => {
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([{ archivo_id: 1, nombre: "a.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" }]),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos/1/contenido`, () =>
        new HttpResponse(new Blob(["%PDF-1.6"], { type: "application/pdf" }), {
          headers: { "Content-Type": "application/pdf" },
        }),
      ),
    );
    renderizar({ controlId: 5, tieneLicencia: false });
    await userEvent.click(await screen.findByRole("button", { name: /ver a\.pdf/i }));
    await waitFor(() => expect(abrir).toHaveBeenCalledWith("blob:documento", "_blank", "noopener"));
  });

  it("sin documentos y con licencia avisa que la biblioteca está vacía", async () => {
    server.use(http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () => HttpResponse.json([])));
    renderizar({ controlId: 5, tieneLicencia: true });
    expect(await screen.findByText(/sin documentos en la biblioteca de salutem/i)).toBeInTheDocument();
  });

  it("si SALUTEM no entrega el contenido muestra el error", async () => {
    server.use(
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos`, () =>
        HttpResponse.json([{ archivo_id: 1, nombre: "a.pdf", tipo: "documento", fecha_creacion: "2026-10-15T16:29:00" }]),
      ),
      http.get(`${BASE}/api/v1/controles-medicos/5/archivos/1/contenido`, () =>
        HttpResponse.json({ detail: "SALUTEM no entregó el contenido del archivo" }, { status: 404 }),
      ),
    );
    renderizar({ controlId: 5, tieneLicencia: false });
    await userEvent.click(await screen.findByRole("button", { name: /ver a\.pdf/i }));
    expect(await screen.findByText(/no se pudo abrir el documento/i)).toBeInTheDocument();
    expect(abrir).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/features/controles/DocumentosSalutem.test.tsx`
Expected: FAIL con `Failed to resolve import "./DocumentosSalutem"`.

- [ ] **Step 4: Write minimal implementation**

En `frontend/src/features/controles/api.ts`:

```ts
export type ArchivoControlRead = components["schemas"]["ArchivoControlRead"];

/** GET /api/v1/controles-medicos/{control_id}/archivos */
export async function archivosDeControl(controlId: number): Promise<ArchivoControlRead[]> {
  const { data, error } = await api.GET("/api/v1/controles-medicos/{control_id}/archivos", {
    params: { path: { control_id: controlId } },
  });
  if (error || !data) throw new Error("No se pudieron cargar los documentos de SALUTEM");
  return data;
}

/**
 * Abre un documento de SALUTEM en una pestaña nueva. Se pide con la sesión (Bearer)
 * y se abre como blob: una URL directa del backend no llevaría el token.
 */
export async function abrirArchivoDeControl(controlId: number, archivoId: number): Promise<void> {
  const { data, error } = await api.GET(
    "/api/v1/controles-medicos/{control_id}/archivos/{archivo_id}/contenido",
    { params: { path: { control_id: controlId, archivo_id: archivoId } }, parseAs: "blob" },
  );
  if (error || !data) throw new Error("No se pudo abrir el documento");
  const url = URL.createObjectURL(data as Blob);
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
```

En `frontend/src/features/controles/hooks.ts`:

```ts
export function useArchivosDeControl(controlId: number, habilitado = true) {
  return useQuery({
    queryKey: ["controles", controlId, "archivos"],
    queryFn: () => archivosDeControl(controlId),
    enabled: habilitado && controlId > 0,
  });
}
```

(importar `archivosDeControl` desde `./api`; seguir el estilo de `useControl` para el `queryKey` si usa otra raíz).

`frontend/src/features/controles/DocumentosSalutem.tsx`:

```tsx
import { FileText } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { abrirArchivoDeControl } from "./api";
import { useArchivosDeControl } from "./hooks";

function fmtFechaHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [fecha, hora = ""] = iso.split("T");
  const [a, m, d] = fecha.split("-");
  return `${d}-${m}-${a} ${hora.slice(0, 5)}`.trim();
}

interface Props {
  controlId: number;
  tieneLicencia: boolean;
}

/** Documentos que el médico subió a la biblioteca de SALUTEM para este control. */
export function DocumentosSalutem({ controlId, tieneLicencia }: Props) {
  const { data: archivos = [], isLoading, isError } = useArchivosDeControl(controlId);

  const ver = async (archivoId: number) => {
    try {
      await abrirArchivoDeControl(controlId, archivoId);
    } catch {
      toast.error("No se pudo abrir el documento. SALUTEM no lo entregó; ábrelo directamente en SALUTEM.");
    }
  };

  return (
    <div data-testid={`documentos-salutem-${controlId}`}>
      <p className="mb-1.5 text-[11.5px] font-medium uppercase tracking-wide text-muted-foreground">
        Documentos en SALUTEM
      </p>
      {isLoading ? (
        <p className="text-[13px] text-muted-foreground">Cargando documentos…</p>
      ) : isError ? (
        <p className="text-[13px] text-destructive">No se pudieron cargar los documentos de SALUTEM.</p>
      ) : archivos.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          {tieneLicencia
            ? "Sin documentos en la biblioteca de SALUTEM para este control."
            : "Sin documentos para este control."}
        </p>
      ) : (
        <ul className="space-y-1">
          {archivos.map((a) => (
            <li key={a.archivo_id} className="flex items-center gap-2 text-[13px]">
              <FileText className="size-3.5 text-muted-foreground" />
              <span className="truncate">{a.nombre}</span>
              <span className="font-mono text-[11.5px] text-muted-foreground">
                {fmtFechaHora(a.fecha_creacion)}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="ml-auto h-7"
                aria-label={`Ver ${a.nombre}`}
                onClick={() => ver(a.archivo_id)}
              >
                Ver
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

En `ControlesPage.tsx`, dentro del `<dl>` del detalle (después de "Observaciones"), solo para controles de SALUTEM:

```tsx
              {control.origen === "SALUTEM" && (
                <div className="sm:col-span-3">
                  <DocumentosSalutem controlId={control.id} tieneLicencia={control.tiene_licencia} />
                </div>
              )}
```

e importar `DocumentosSalutem`. El detalle solo se monta al desplegarlo, así que la consulta de archivos no corre para todas las filas.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/features/controles && npm run typecheck`
Expected: PASS y typecheck sin errores. Si el texto de la fecha no coincide con la expresión del test, ajustar `fmtFechaHora` (no el test): debe mostrar `15-10-2026 16:29`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/features/controles/api.ts frontend/src/features/controles/hooks.ts frontend/src/features/controles/DocumentosSalutem.tsx frontend/src/features/controles/DocumentosSalutem.test.tsx frontend/src/features/controles/ControlesPage.tsx
git commit -m "feat(controles): documentos de SALUTEM en el detalle del control

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 7: Frontend — panel de alertas y configuración

**Files:**
- Create: `frontend/src/components/shell/DocumentosAlertaDialog.tsx`
- Modify: `frontend/src/components/shell/AlertsPanel.tsx:213-215, 291-309` (títulos y clic)
- Modify: `frontend/src/features/config-alertas/api.ts:9-18` (etiquetas y tipos sin días)
- Modify: `frontend/src/features/config-alertas/ConfigAlertasPage.tsx:116-165` (sin días ni hábiles para esos tipos)
- Test: `frontend/src/components/shell/AlertsPanel.test.tsx`, `frontend/src/features/config-alertas/ConfigAlertasPage.test.tsx`

**Interfaces:**
- Consumes: `DocumentosSalutem` y `useControl` (Tarea 6 y existente).
- Produces: `TITULOS_ALERTA: Record<string, string>` y `tituloAlerta(tipo: string): string` en `AlertsPanel.tsx`; `TIPOS_ALERTA_CONTROL = ["licencia_en_control", "receta_en_control"]` y `TIPOS_SIN_DIAS` en `config-alertas/api.ts`.

- [ ] **Step 1: Write the failing tests**

En `AlertsPanel.test.tsx`:

```tsx
import { tituloAlerta } from "./AlertsPanel";

describe("tituloAlerta", () => {
  it("nombra las alertas de licencia y receta del control", () => {
    expect(tituloAlerta("licencia_en_control")).toBe("Licencia emitida en control");
    expect(tituloAlerta("receta_en_control")).toBe("Receta emitida en control");
  });

  it("los demás tipos conservan su título derivado", () => {
    expect(tituloAlerta("vencimiento_licencia")).toBe("Vencimiento licencia");
  });
});
```

Y un test de render del panel con MSW (seguir el patrón de `EvaluacionControlDialog.test.tsx` para token, `AuthProvider`, `MemoryRouter` y `QueryClientProvider`): con `GET /api/v1/alertas` devolviendo
`[{ id: 1, tipo: "licencia_en_control", estado: "pendiente", caso_id: 5, caso_tipo: "control_medico", usuario_id: null, plazo_objetivo: "2026-10-15T00:00:00Z", ventana_dias: 0, generada_en: "2026-10-15T19:35:00Z", resuelta_en: null, email_enviado: false }]`,
`GET /api/v1/tareas` devolviendo `[]`, `GET /api/v1/controles-medicos/5` devolviendo un control (`fecha_control: "2026-10-15"`, `medico_tratante: "DRA. PAULA ROJAS"`, `tiene_licencia: true`, `resumen_termino_lm: "LM tipo 6 por 30 días"`, `origen: "SALUTEM"`) y `GET /api/v1/controles-medicos/5/archivos` devolviendo un archivo `"LICENCIA.pdf"`:

```tsx
it("al hacer clic en una alerta de licencia abre el control con sus documentos", async () => {
  // ...render <AlertsPanel /> con los handlers de arriba...
  await userEvent.click(await screen.findByText("Licencia emitida en control"));
  const dialogo = await screen.findByRole("dialog");
  expect(within(dialogo).getByText(/DRA\. PAULA ROJAS/)).toBeInTheDocument();
  expect(within(dialogo).getByText(/LM tipo 6 por 30 días/)).toBeInTheDocument();
  expect(await within(dialogo).findByText("LICENCIA.pdf")).toBeInTheDocument();
  expect(within(dialogo).getByRole("button", { name: /ir a controles/i })).toBeInTheDocument();
});
```

Si el `AlertsPanel` real vive dentro de un `Popover`/`Sheet` que hay que abrir primero, abrirlo en el test igual que lo hace el uso existente (buscar el disparador en `Topbar.tsx`), o renderizar el contenido directamente si el componente lo permite.

En `ConfigAlertasPage.test.tsx`, con `GET /api/v1/config-alertas` incluyendo `{ tipo: "licencia_en_control", dias: 0, habiles: false, activo: true }`:

```tsx
it("las alertas del control solo se encienden o apagan", async () => {
  // ...render como en los tests existentes del archivo...
  const fila = await screen.findByTestId("fila-licencia_en_control");
  expect(within(fila).getByText("Licencia emitida en control")).toBeInTheDocument();
  expect(within(fila).queryByLabelText(/días/i)).not.toBeInTheDocument();
  expect(within(fila).queryByLabelText(/hábiles/i)).not.toBeInTheDocument();
  expect(within(fila).getByLabelText(/activo/i)).toBeInTheDocument();
});
```

(usar la etiqueta real del checkbox "Activo" que ya tiene la página).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/shell/AlertsPanel.test.tsx src/features/config-alertas`
Expected: FAIL (`tituloAlerta` no existe; la fila muestra el input de días).

- [ ] **Step 3: Write minimal implementation**

En `frontend/src/features/config-alertas/api.ts`:

```ts
export const TIPO_LABELS: Record<string, string> = {
  // ...los existentes...
  licencia_en_control: "Licencia emitida en control",
  receta_en_control: "Receta emitida en control",
};

/** Alertas del sync de SALUTEM: no tienen plazo, solo se encienden o apagan. */
export const TIPOS_SIN_DIAS = new Set(["licencia_en_control", "receta_en_control"]);
```

En `ConfigAlertasPage.tsx`, con `const sinDias = TIPOS_SIN_DIAS.has(f.tipo);`, envolver la celda de días y la de hábiles para que con `sinDias` muestren `<span className="text-[13px] text-muted-foreground">—</span>` (igual que hoy la de hábiles para GAF), y bajo el nombre:

```tsx
{sinDias && (
  <p className="text-[11.5px] font-normal text-muted-foreground">
    Llega cuando el sync de SALUTEM trae un control con esta indicación
  </p>
)}
```

`frontend/src/components/shell/DocumentosAlertaDialog.tsx`:

```tsx
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { useControl } from "@/features/controles/hooks";
import { DocumentosSalutem } from "@/features/controles/DocumentosSalutem";

interface Props {
  titulo: string;
  controlId: number | null;
  onOpenChange: (open: boolean) => void;
}

/** El control de una alerta de licencia o receta, con sus documentos de SALUTEM. */
export function DocumentosAlertaDialog({ titulo, controlId, onOpenChange }: Props) {
  const navigate = useNavigate();
  const { data: control, isLoading } = useControl(controlId ?? 0);

  return (
    <Dialog open={controlId !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>
            Revisa la indicación del médico y los documentos que subió a SALUTEM.
          </DialogDescription>
        </DialogHeader>
        {isLoading || !control ? (
          <p className="text-[13px] text-muted-foreground">Cargando control…</p>
        ) : (
          <div className="space-y-3 text-[13px]">
            <p>
              Control del {control.fecha_control.split("-").reverse().join("-")} · {control.medico_tratante}
            </p>
            {control.resumen_termino_lm && (
              <p className="rounded-md bg-muted/40 p-2">{control.resumen_termino_lm}</p>
            )}
            <DocumentosSalutem controlId={control.id} tieneLicencia={control.tiene_licencia} />
          </div>
        )}
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              onOpenChange(false);
              navigate("/controles");
            }}
          >
            Ir a Controles
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

Confirmar que `useControl` en `features/controles/hooks.ts` deshabilita la consulta con id 0 (`enabled: controlId > 0`); si no, agregarlo.

En `AlertsPanel.tsx`:

```tsx
export const TITULOS_ALERTA: Record<string, string> = {
  licencia_en_control: "Licencia emitida en control",
  receta_en_control: "Receta emitida en control",
};

export function tituloAlerta(tipo: string): string {
  return TITULOS_ALERTA[tipo] ?? cap(tipo.replace(/_/g, " "));
}
```

En `AlertsPanel()`: `const [alertaControl, setAlertaControl] = useState<AlertaRead | null>(null);`; `handleAlertaClick` pasa a:

```tsx
  const handleAlertaClick = (a: AlertaRead) => {
    if (a.tipo in TITULOS_ALERTA) {
      setAlertaControl(a);
      return;
    }
    navigate(routeForCaso(a.caso_tipo, a.caso_id));
  };
```

en el `map` de alertas: `const title = tituloAlerta(a.tipo);`, y al final del JSX del panel:

```tsx
      <DocumentosAlertaDialog
        titulo={alertaControl ? tituloAlerta(alertaControl.tipo) : ""}
        controlId={alertaControl?.caso_id ?? null}
        onOpenChange={(open) => !open && setAlertaControl(null)}
      />
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run && npm run typecheck && npm run lint`
Expected: PASS en toda la suite, typecheck y lint sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/shell/DocumentosAlertaDialog.tsx frontend/src/components/shell/AlertsPanel.tsx frontend/src/components/shell/AlertsPanel.test.tsx frontend/src/features/config-alertas/api.ts frontend/src/features/config-alertas/ConfigAlertasPage.tsx frontend/src/features/config-alertas/ConfigAlertasPage.test.tsx
git commit -m "feat(alertas): licencia y receta del control en el panel y en la configuración

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarea 8: Verificación completa, runbook y validación en QA

**Files:**
- Modify: `docs/operacion/salutem-sync.md` (sección nueva)

- [ ] **Step 1: Suites completas**

```bash
cd backend && "$PY/pytest" -q
cd ../frontend && npx vitest run && npm run typecheck && npm run lint && npm run build
```

Expected: todo verde. Si algo ajeno a esta feature falla, anotarlo y no corregirlo en esta rama.

- [ ] **Step 2: Migración en Postgres de cero**

```bash
cd backend && "$PY/alembic" downgrade 1310 && "$PY/alembic" upgrade head
```

Expected: sin errores (contra la BD local de desarrollo, no la de tests).

- [ ] **Step 3: Documentar en el runbook**

Agregar a `docs/operacion/salutem-sync.md`:

```markdown
## Biblioteca de archivos y alertas de licencia/receta (2026-10)

- El ciclo `caliente`, después de vincular, lista `/personas-archivos` de las personas con un
  control de los últimos 7 días y guarda solo la metadata en `salutem_archivo` (migración 1320).
  El contenido nunca se copia: el botón "Ver" lo pide a SALUTEM al abrirlo.
- La vinculación crea las alertas `licencia_en_control` y `receta_en_control` (una por control y
  tipo; solo controles de los últimos 14 días). Se apagan en `/config-alertas`.
- La API de SALUTEM no informa carpeta ni cita del archivo: se unen al control por fecha.
- En QA los archivos antiguos llegan con `archivo_base64` vacío; los subidos recientemente sí traen
  contenido.
- Despliegue: aplicar la migración (`alembic upgrade head`) antes de reiniciar la API y el cron.
```

- [ ] **Step 4: Validación manual en QA (en la VM de desarrollo)**

Después de desplegar la rama en la VM dev (procedimiento habitual del runbook de despliegue):
1. Esperar un ciclo `caliente` (~5 min) y revisar en el log del sync la línea `Biblioteca SALUTEM: N personas revisadas`.
2. En SIGE, Controles → paciente "Humberto Escobar prueba" (`persona_id` 1180505) → control "Médico/a" del 15-10-2026 → desplegar el detalle: deben aparecer `DesafiliacionElectronica.pdf` y `boletaPPL ripley.pdf`, y "Ver" debe abrir cada PDF.
3. **Pendiente de confirmar con Pilar:** que emita una receta de prueba en ese control (por ejemplo "Clotiazepam 5 mg 0-0-1") y una indicación de reposo. Tras el ciclo siguiente, deben aparecer en el panel "Receta emitida en control" y "Licencia emitida en control". Si la receta no llega como indicación `Receta Medicamentos` ni en un campo "Indicaciones", avisar: la regla de `tiene_receta` necesita otra señal.

- [ ] **Step 5: Commit**

```bash
git add docs/operacion/salutem-sync.md
git commit -m "docs(salutem-sync): biblioteca de archivos y alertas de licencia/receta

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
