# Diseño — Pacientes borrador desde SALUTEM, pendientes de folio

> **Estado:** diseño acordado en conversación el 2026-10-16; pendiente de revisión de esta spec.
> **Alcance:** solo lectura sobre SALUTEM (v4 D12). Amplía el sync de SALUTEM, el modelo de
> paciente, el motor de alertas (`alerta_notif`) y el alta de ingreso. Construye sobre el PR #46
> (alertas de licencia/receta, visibilidad de alertas sin asignar para Administrativas).

## Objetivo

Que ninguna persona atendida en el CEPA quede fuera del SIGE. Cuando SALUTEM atiende a alguien
que todavía no existe en el SIGE, el sistema crea un **paciente borrador** con sus datos de
SALUTEM, lo marca **"Pendiente de folio"** y avisa a las administrativas. Una administrativa lo
revisa y **registra su folio en la ficha del paciente**, lo que crea el ingreso y completa el
registro. Mientras tanto, el paciente lleva una **señal visible** de que le falta el folio.

**Éxito:** cada persona nueva atendida desde la fecha de corte aparece una sola vez en la lista
"Pendientes de folio" a los ~5 minutos del sync; al registrarle el folio desaparece de la lista
y, en el ciclo siguiente, quedan unidas sus atenciones, controles y documentos de SALUTEM.

## Contexto (estado actual)

- Un paciente solo existe en el SIGE si alguien le crea un ingreso, y el ingreso exige folio
  (`ingreso.folio` NOT NULL: manual o correlativo automático, `services/folio.py`).
- El folio es llave de texto entre tablas: `ficha_clinica.folio` e `imed_payload.folio`.
- El sync copia personas y atenciones de SALUTEM (`salutem_persona`, `salutem_atencion`) y la
  vinculación solo une atenciones a pacientes que ya existen (por RUT o `salutem_persona_id`,
  `filtro.cruce_con_paciente`). Una persona sin paciente en el SIGE hoy no aparece en ningún lado.
- La vinculación ya trae las atenciones de un paciente cuyo ingreso se creó después de la
  corrida anterior (`ingresos_desde`): no hace falta vincular a mano al completar un borrador.
- `paciente.rut`, `sexo`, `edad` y `region` son NOT NULL, y el alta de ingreso los exige. En
  SALUTEM hay personas sin RUT (`tipoIdentificacion` "SIN IDENTIFICACION", identificación
  `sin_id_…`) y SALUTEM no informa región.
- Las licencias escritas en SALUTEM **no traen folio** (spike del 2026-10-16: 150 atenciones de
  control de enero 2026, ninguna menciona folio ni números de 6+ dígitos). El folio del que
  habla esta spec es el **folio del paciente/caso del CEPA**.

## Decisiones

1. **Enfoque A — paciente borrador sin ingreso.** No se inventan folios temporales ni datos de
   ingreso de relleno: el folio es la identidad oficial del caso en el CEPA.
2. **Fecha de corte configurable** (`SALUTEM_BORRADORES_DESDE`, fecha ISO). Solo generan
   borrador las personas con al menos una atención Atendida en o después de esa fecha. Vacía =
   funcionalidad apagada (no se crean borradores). Por defecto, al desplegar, se configura con el
   día de activación. La historia anterior entra por la migración de la planilla (COMP-2609-30).
3. **Descartar** un borrador (persona que no es un caso del CEPA): queda guardado con motivo y el
   sync no lo vuelve a crear.
4. **Alerta** "Paciente nuevo pendiente de folio" por cada borrador, sin profesional asignado (la
   ven todas las Administrativas y Coordinación).
5. En las VMs sigue rigiendo `SALUTEM_SYNC_PERSONAS_PERMITIDAS`: solo se copian (y por lo tanto
   solo pueden generar borrador) las personas de prueba.

## Componentes

### 1. Modelo — migración 1330 (`paciente`)

| Cambio | Detalle |
|---|---|
| `estado_registro` String(20) NOT NULL, default `completo` | `completo` · `pendiente_folio` · `descartado` |
| `origen` String(10) NOT NULL, default `SIGE` | `SIGE` · `SALUTEM` |
| `motivo_descarte` String(300) NULL | Solo con `descartado` |
| `descartado_por` String(80) NULL, `descartado_en` DateTime(tz) NULL | Quién y cuándo |
| `rut`, `sexo`, `edad`, `region` pasan a NULL | Un borrador puede no traerlos. `rut` mantiene UNIQUE (Oracle y Postgres admiten varios NULL) |

Índice `ix_paciente_estado_registro`. Los pacientes existentes quedan `completo` / `SIGE`.
Identificadores ≤ 30 caracteres (D15). Enum de dominio `EstadoRegistroPaciente` en
`app/domain/enums.py`.

**Regla:** un paciente `completo` sigue teniendo siempre RUT (o identificación de SALUTEM, ver
§4), sexo, edad y región: la obligatoriedad se mueve de la base al alta de ingreso.

### 2. Creación de borradores — `app/services/salutem_sync/borradores.py` (nuevo)

Se ejecuta al final de cada ciclo (`caliente`, `tibia`, `fria`, `backfill`, `vincular`), después
de la vinculación, en el orquestador:

- Si `SALUTEM_BORRADORES_DESDE` está vacía → no hace nada.
- Candidatas: `salutem_persona` con al menos una `salutem_atencion` no desaparecida, con
  `fecha_cita >= corte` y `contenido.estadoCitaId == ATENDIDO`, y **sin** paciente que cumpla
  `cruce_con_paciente()` (cualquier `estado_registro`, incluidos los descartados).
- Por cada candidata crea un `Paciente`:
  - `nombre` = `nombres` + `apellidos` de SALUTEM (recortado a 160; si faltan, la identificación).
  - `rut` = RUT normalizado si la identificación es un RUT válido; si no, NULL.
  - `salutem_persona_id` = id de SALUTEM.
  - `sexo` = HOMBRE→`M`, MUJER→`F`, otro valor→`otro`, ausente→NULL.
  - `edad` = años cumplidos desde `fechaNacimiento` (DD-MM-AAAA) a hoy (Santiago); ilegible→NULL.
  - `comuna` = comuna de SALUTEM (recortada a 80). `region` = NULL. `telefono`/`correo` desde
    SALUTEM si vienen (`telefonoMovil`, `email`), recortados.
  - `estado_registro = pendiente_folio`, `origen = SALUTEM`.
- Crea la alerta (§3) y registra auditoría (`actor = sistema:salutem-sync`, `CREATE paciente`).
- Idempotente: una persona con paciente (en cualquier estado) nunca vuelve a ser candidata.
- Un error en una persona (datos inesperados) se registra en la bitácora y no detiene a las
  demás ni al ciclo (savepoint por persona, mismo patrón que la vinculación).

### 3. Alerta `paciente_pendiente_folio`

- `TipoAlerta.PACIENTE_PENDIENTE_FOLIO = "paciente_pendiente_folio"`; `caso_tipo = "paciente"`,
  `caso_id = paciente.id`, `usuario_id = NULL`, `plazo_objetivo` = fecha de creación del borrador
  (medianoche UTC), `ventana_dias = 0`.
- `VENTANAS_DEFAULT` la suma encendida (`dias 0`, solo encender/apagar, como las de control). Con
  el tipo apagado no se crea la alerta, pero el borrador sí.
- Se **resuelve sola** al completar el registro (§5) o al descartar (§4).
- Panel: título "Paciente nuevo pendiente de folio"; clic → la ficha del paciente.

### 4. API

Rol: **solo Administrativo y Coordinación** (lista, descartar y completar). El Auditor no ve la
lista; en el buscador y la ficha sí ve la señal "Falta folio" (solo lectura).

- `GET /api/v1/pacientes/pendientes-folio` → `[PacientePendienteRead]`, más antiguos primero:
  `id`, `nombre`, `rut` (o NULL), `identificacion_salutem` (`sin_id_…` cuando no hay RUT),
  `salutem_persona_id`, `creado_en`, y un resumen de SALUTEM calculado de la copia:
  `primera_atencion`, `ultima_atencion`, `atenciones` (cantidad), `especialidades` (distintas,
  máx. 5).
- `POST /api/v1/pacientes/{id}/descartar` con `{motivo}` (1–300 caracteres) → 200 con el
  paciente. Solo desde `pendiente_folio` (otro estado → 409). Resuelve la alerta, audita.
- `PacienteRead` (buscador, ficha) suma `estado_registro` y `origen`; `rut`, `sexo`, `edad` y
  `region` pasan a opcionales en el schema.
- `GET /api/v1/pacientes/buscar` incluye los `pendiente_folio` (con su estado) y **excluye** los
  `descartado`. La lista de Ingresos no cambia (los borradores no tienen ingreso).
- **Completar el registro = crear el ingreso.** `IngresoCreate` suma `paciente_id: int | None`:
  - Con `paciente_id` de un paciente `pendiente_folio`: se usa ese paciente (no se busca por RUT),
    se actualizan sus datos con lo enviado, se crea el ingreso con el flujo actual de folio
    (manual o correlativo, mismas validaciones y 409 por colisión) y el paciente pasa a
    `completo`; se resuelve su alerta; auditoría `UPDATE paciente` + la del ingreso.
  - `rut` pasa a opcional en `IngresoCreate` **solo** cuando viene `paciente_id` y el paciente no
    tiene RUT (persona sin identificación en SALUTEM); en cualquier otro caso sigue obligatorio y
    con validación de DV. Si se envía un RUT que ya tiene otro paciente → 409 (indicar descartar
    el borrador si es la misma persona).
  - `sexo`, `edad`, `region` siguen obligatorios: la admin los completa en el formulario.
  - Con `paciente_id` de un paciente `completo` o `descartado` → 409.

### 5. Frontend

- **Menú:** "Pendientes de folio" (solo Administrativo y Coordinación), con un contador de
  pendientes.
- **Pantalla Pendientes de folio:** tabla con nombre, RUT o identificación de SALUTEM, fechas de
  primera/última atención, especialidades y cantidad de atenciones. Acciones:
  "Completar registro" (lleva a la ficha y abre el formulario) y "Descartar" (diálogo con motivo
  obligatorio).
- **Señal "Falta folio":** distintivo en los resultados del buscador de pacientes (página y
  buscador lateral) y en el encabezado de la ficha / vista 360 del paciente. En la ficha, aviso
  "Este paciente viene de SALUTEM y le falta el folio para completar su registro" con el botón
  **"Completar registro"** (escritores).
- **Completar registro:** el formulario de alta de ingreso existente, precargado con los datos
  del paciente, enviando `paciente_id`. El campo folio funciona como hoy (manual o correlativo).
  Si el paciente no tiene RUT, el campo RUT es opcional y muestra la identificación de SALUTEM.
- Los componentes que muestran RUT, sexo, edad o región toleran valores nulos (muestran "—").

## Errores y bordes

- Persona de SALUTEM que ya está en el SIGE con otro RUT (o sin `salutem_persona_id`): se crea un
  borrador duplicado; la admin lo descarta con motivo "ya existe como …". Unir pacientes queda
  fuera de alcance.
- RUT de SALUTEM inválido: el borrador se crea sin RUT; la admin lo completa.
- Persona con atenciones anteriores al corte y una nueva posterior: genera borrador (basta una
  atención desde el corte).
- Atención anulada después de crear el borrador: el borrador se mantiene (la admin decide).
- `SALUTEM_BORRADORES_DESDE` con formato inválido: se registra el error al arrancar el ciclo y no
  se crean borradores (no detiene el sync).
- Dos ciclos simultáneos: el lease del sync ya lo impide.

## Pruebas (TDD)

- Sync: crea un borrador por persona atendida desde el corte; no crea sin corte; ignora
  atenciones anteriores al corte y no atendidas; no duplica en ciclos siguientes; no recrea
  descartados; no crea si la persona ya cruza con un paciente por RUT o por id; mapeo de nombre,
  RUT (válido/ inválido/ sin id), sexo, edad, comuna; error en una persona no detiene a las demás.
- Alerta: se crea con el borrador; tipo apagado → no; se resuelve al completar y al descartar.
- API: lista (orden, resumen, permisos: Auditor 403), descartar (motivo, 409 desde otro
  estado), buscador incluye pendientes y excluye descartados, completar con `paciente_id` (folio
  manual y automático, RUT opcional solo sin RUT, 409 por RUT de otro paciente y por paciente no
  pendiente), paciente pasa a `completo`.
- Migración 1330: sube y baja en Postgres; probar en la Oracle de QA antes de dev.
- Frontend: lista y contador, distintivo en buscador y ficha, descartar, completar registro con
  precarga y envío de `paciente_id`, campos nulos sin romper.
- Validación en QA: configurar el corte, verificar que el paciente de prueba nuevo aparezca y que
  al completarlo se unan sus atenciones en el ciclo siguiente.

## Fuera de alcance

- Migración de la planilla histórica (COMP-2609-30).
- Unir pacientes duplicados.
- Reglas del folio por programa y sigla (PA-v5-01; tarea "Generar el folio … correlativo con
  sigla").
- Anonimización (tarea aparte; esta lista es solo para roles internos).
