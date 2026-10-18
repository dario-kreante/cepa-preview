# Diseño — Fase 2: tabla `cita` alimentada desde SALUTEM

> **Estado:** borrador definido por Claude el 2026-10-16 a pedido del usuario. Las decisiones
> marcadas **[CEPA]** dependen de preguntas abiertas al CEPA (al final del documento). Mientras
> no haya respuesta se implementa la opción **por defecto** que indica cada una, y se valida en el
> periodo de pruebas.
> **Alcance:** solo lectura sobre SALUTEM (v4 D12). Amplía el sync de SALUTEM y la tabla `cita`.
> Construye sobre la Fase 1 (PR #53, "Pacientes por citar"), que retira la confirmación de
> propuestas, hasta ahora la única fuente real de filas en `cita`.

## Objetivo

Que las alertas de citas digan la verdad y que los reportes que cuentan citas (adherencia, operativo, convenio, carga por profesional y
dashboard) vuelvan a recibir datos, y que esos datos sean reales: las horas que SALUTEM agendó,
atendió, anuló o marcó como inasistencia para los pacientes del CEPA.

**Éxito:** a los ~5 minutos de que una cita cambia en SALUTEM (se crea, se atiende, se anula o
se marca inasistencia), la fila correspondiente de `cita` refleja ese estado, y los reportes del
período lo cuentan sin intervención manual.

## Contexto (estado actual)

- `cita` (`app/models/cita.py`) tiene `id`, `ingreso_id`, `estado` (`agendada` | `realizada` |
  `inasistencia` | `anulada`), `fecha` y `created_at`. Hasta la Fase 1 se llenaba solo desde
  `confirmar_citas` (DD-1) y desde el seed de desarrollo. La BD de desarrollo local tiene 240
  filas, todas del seed.
- La leen:
  - `reporte_adherencia`: realizadas / todas las citas del folio.
  - `reporte_operativo` y `reporte_convenio`: conteos por estado y período.
  - `reporte_carga`: casos y atenciones realizadas por `Ingreso.profesional_id`.
  - `dashboard`: conteos por estado y convenio.

  El período siempre se aplica sobre `cita.fecha` (DD-4).
- `PATCH /api/v1/citas/{id}/estado` permite transiciones manuales
  (`agendada → realizada | inasistencia | anulada`, y de ahí a `anulada`). Hoy el frontend no la
  usa.
- El sync copia en `salutem_cita` (`copia.guardar_cita`) **todas las citas de cada día barrido en
  SALUTEM**, no solo las de las personas del CEPA. Solo filtra cuando hay una lista de personas
  permitidas (`filtro.envolver_si_corresponde`), y producción no tiene esa lista. Cada fila guarda:
  `cita_id`, `persona_id`, `fecha_cita` (nullable), `fecha_creacion`, `estado_id` y el JSON
  `contenido`, que trae `especialidadNombre` y `profesionalNombre`. Las filas tienen `cambiado_en`
  y `desaparecida_en`. A diferencia de `salutem_atencion`, no tienen `hash_vinculado`.
- El barrido vuelve a leer cada fecha solo dentro de una ventana: la tibia cubre de −7 a +30 días
  y la fría de −90 a +180. Si una cita más antigua que eso cambia de estado en SALUTEM, el cambio
  solo llega con un `backfill`.
- `EstadoCitaSalutem` tiene los estados AGENDADO 1, ANULADO 2, ATENDIDO 3, AGENDADO_WEB 4,
  CONFIRMADO 5, CONFIRMADO_WEB 6, CONFIRMADO_EMAIL 7, RECEPCIONADO 8 y NO_ASISTE 9.
- La atribución persona → paciente ya existe (`filtro.cruce_con_paciente`, por RUT o
  `salutem_persona_id`), y también la de fecha → ingreso (`ficha_clinica._en_ventana_del_ingreso`:
  desde `fecha_ingreso` y, si el caso cerró, hasta `fecha_alta`).

## Decisiones

1. **`cita` pasa a ser un espejo de las citas SALUTEM de los pacientes del CEPA.** Se agregan las
   columnas:
   - `salutem_cita_id` (BigInteger, nullable, único), que es la llave del upsert.
   - `origen` (String(10), `SALUTEM` | `SIGE`, server_default `SIGE`).
   - `especialidad` (String(80), nullable).
   - `profesional_nombre` (String(160), nullable).
   - `profesional_id` (BigInteger, FK a `profesional.id`, nullable), resuelto por
     `profesional.nombre = TRIM(profesional_nombre)`, el mismo criterio de la Fase 1.
     *(Decisión de Claude)* El sync **no** da de alta profesionales en el catálogo, porque eso
     llenaría el selector de Agendamiento con gente que no se agenda. `profesional_id` solo enlaza
     a los que ya existen.
   - *(Decisión de Claude)* Si `profesionalNombre` viene vacío o es el marcador
     `SIN_PROFESIONAL_SALUTEM`, `profesional_nombre` queda en NULL.

   En Oracle, un índice único sobre una columna con NULL acepta varias filas NULL, así que las
   filas antiguas sin `salutem_cita_id` no chocan.
2. **Correspondencia de estados.**

   | `salutem_cita.estado_id` | `cita.estado` |
   |---|---|
   | ATENDIDO | `realizada` |
   | NO_ASISTE | `inasistencia` |
   | ANULADO | `anulada` |
   | AGENDADO, AGENDADO_WEB, CONFIRMADO, CONFIRMADO_WEB, CONFIRMADO_EMAIL | `agendada` |
   | RECEPCIONADO | `agendada` **[CEPA, P7]** |

   Un `estado_id` desconocido o nulo no se importa y se registra en el log del sync como aviso.
3. **A qué ingreso pertenece la cita.** Primero la persona se cruza con el paciente por
   `cruce_con_paciente`, **en SQL**: un join entre `salutem_cita`, `salutem_persona` y `paciente`.
   Como la tabla tiene todo SALUTEM, el filtro va primero en la consulta y no en Python. Las citas
   de personas que no son pacientes del CEPA se ignoran sin contarlas ni registrarlas.
   `especialidadNombre` y `profesionalNombre` se leen del JSON en Python, solo para las filas que
   pasan el cruce, porque `PortableJSON` en Oracle no permite filtrarlos bien en SQL. Una cita sin
   `fecha_cita` no se importa. Luego se buscan los ingresos de ese paciente en cuya ventana cae
   `fecha_cita` (`_en_ventana_del_ingreso`). Si hay más de uno, se usa el de `fecha_ingreso` más
   reciente. Si no hay ninguno, la cita no se importa **[CEPA, P6]**: no pertenece a ningún
   episodio del CEPA. Si la cita ya estaba importada y deja de caer en una ventana (por ejemplo,
   porque cambió la fecha de alta), se elimina. Los reportes agrupan por convenio y por
   especialidad según el ingreso elegido aquí.
4. **Qué especialidades se importan [CEPA, P1].** Se importan todas y se guarda la `especialidad`.
   Los reportes filtran con la configuración `CITAS_ESPECIALIDADES_REPORTES`, una lista separada
   por comas; vacía, cuenta todas. **Por defecto queda vacía (todas).** Así, cambiar el criterio
   no obliga a reimportar.
5. **Cita que desaparece de SALUTEM** (`desaparecida_en` informado): se elimina la fila de `cita`
   y se audita como `DELETE`, igual que hace el sync con los controles. La razón es que una cita
   borrada en SALUTEM nunca existió para el CEPA, a diferencia de una anulada, que sí cuenta.
   *(Decisión de Claude)* Si una cita se reprograma, puede quedar marcada como desaparecida por un
   momento y reaparecer en otra fecha. En ese caso la fila se borra y se vuelve a crear con otro
   `id`. Se acepta porque ninguna tabla referencia `cita.id`.
6. **Cuándo corre.** Se agrega un paso nuevo al orquestador, después de la vinculación y los
   borradores: `salutem_sync/citas_cepa.py::sincronizar_citas(db, desde: datetime | None, ahora)`.
   Revisa las `salutem_cita` con `cambiado_en >= desde` y también todas las citas de los
   pacientes cuyos ingresos cambiaron desde `desde`, para que un ingreso nuevo traiga sus citas
   antiguas (el mismo patrón que `ingresos_desde` en la vinculación). `desde = None` revisa todo:
   es el modo `backfill` y el arranque en frío. Cada cita se procesa en un savepoint, para que una
   cita con error no frene a las demás.
6b. **Citas antiguas fuera de la ventana del barrido** *(decisión de Claude)*. Se acepta esa
   limitación: en la práctica, SALUTEM marca "Atendido" o "No asiste" el mismo día de la cita, y
   eso cae dentro de la ventana tibia. Para que el problema se vea, la bitácora de cada corrida
   informa cuántas citas siguen como `agendada` con fecha de hace más de 90 días. Si ese número
   crece, se corre el `backfill` de esas fechas. Releer esas fechas automáticamente queda fuera de
   esta fase.
7. **Historial [CEPA, P3].** Se importan las citas con `fecha_cita >= CITAS_SALUTEM_DESDE`, una
   configuración nueva. **Por defecto es el 2026-01-01**, porque los reportes del año completo
   necesitan el año completo. La carga inicial corre con el modo `backfill` ya existente.
8. **Filas que ya existían en `cita` [CEPA, P4].** La migración las marca con `origen='SIGE'`. Por
   defecto se mantienen y los reportes cuentan solo las de `origen='SALUTEM'`, para no duplicar.
   Si el CEPA confirma que esas filas son de prueba, se agrega un script de borrado aparte. En QA
   y en producción casi seguro son confirmaciones de prueba. La BD de desarrollo usa el seed, que
   pasa a crear filas `origen='SALUTEM'` con `salutem_cita_id` ficticio, para que los reportes
   locales sigan mostrando datos.
9. **El estado lo define SALUTEM.** `PATCH /api/v1/citas/{id}/estado` responde 409 sobre las filas
   con `origen='SALUTEM'` ("El estado de esta cita lo informa SALUTEM"). Sobre las filas `SIGE`
   sigue funcionando igual.
10. **Denominador de adherencia [CEPA, P2].** Hoy es "todas las citas del folio". **Por defecto
    pasa a ser `realizada + inasistencia`**: las citas que debían ocurrir y ya ocurrieron o no.
    Las anuladas y las agendadas futuras no castigan la adherencia. Es un cambio de criterio y
    debe quedar explicado en la ayuda del reporte.
11. **Carga por profesional [CEPA, P5].** Hoy se atribuye por `Ingreso.profesional_id`, un entero
    que nadie llena desde la interfaz. **Por defecto pasa a atribuirse por quien realmente atendió:
    se agrupa por `cita.profesional_nombre`** (el texto de SALUTEM sin espacios sobrantes), así
    que psicología, EPT y las demás especialidades también aparecen aunque no estén en el
    catálogo. Si hay `profesional_id`, el reporte lo incluye. Las citas sin nombre se agrupan como
    "Sin profesional informado".
12. **Corregir la alerta "control médico"** (pedido del usuario el 2026-10-16). Hoy
    `_construir_hitos_control_medico` (`services/alertas.py`) avisa por todo control con
    `proximo_control` y `proximo_agendado = false`. Ese campo no ve las horas agendadas en SALUTEM
    después de la atención, así que la alerta sigue activa con el paciente ya citado. Pasa a usar
    el mismo criterio de la Fase 1 (decisión 2 del diseño de Pacientes por citar):
    - En los controles `origen='SALUTEM'` se ignora `proximo_agendado` y no se alerta si el
      paciente tiene una hora vigente en SALUTEM (`agendamiento.salutem.pacientes_con_hora_vigente`).
    - En los controles `origen='CEPA'` se sigue respetando `proximo_agendado`.
    - Solo cuentan ingresos activos.
    - **Autorresolución:** el job diario y el paso de citas del sync marcan como `resuelta` las
      alertas `control_medico` abiertas (pendiente o leída) de pacientes que ya tienen una hora
      vigente. Lo hacen con el actor `sistema:salutem-sync` o `sistema` y quedan auditadas. Así,
      la alerta desaparece a los ~5 minutos de agendar en SALUTEM, igual que el paciente en la
      lista "Pacientes por citar".
13. **Alerta nueva "inasistencia"** (pedido del usuario el 2026-10-16). Cuando el paso de citas
    del sync deja una cita en `inasistencia` (porque llegó así o porque cambió a ese estado):
    - Crea una alerta `TipoAlerta.INASISTENCIA = "inasistencia"` para recontactar al paciente.
      Usa `caso_tipo="salutem_cita"` y `caso_id=salutem_cita_id`, que es estable aunque la fila
      de `cita` se vuelva a crear (decisión 5). `plazo_objetivo` es la fecha de la cita y
      `ventana_dias` es 0.
    - Crea **una sola alerta por cita y para siempre**, aunque la cita cambie y vuelva a quedar
      en inasistencia. Así lo hacen las alertas de licencia y receta en control.
    - Solo alerta por citas de los últimos **14 días** (`DIAS_NOVEDAD`, como en
      `alertas_control`), para que el `backfill` y la carga inicial no llenen el panel con
      inasistencias viejas.
    - Respeta el filtro de especialidades de reportes (decisión 4), con la misma configuración.
    - Destinatario **[CEPA, P8]**: por defecto, `_resolver_usuario(ingreso_id)`, igual que las
      demás alertas. En la práctica casi siempre es nulo, y entonces va al panel global que ven
      Coordinación y las Administrativas.
    - Se resuelve sola cuando el paciente vuelve a tener una hora vigente en SALUTEM (misma
      autorresolución de la decisión 12).
    - Se puede activar o desactivar desde "Umbrales de alerta" como las demás. La migración siembra
      `config_alerta` con `tipo='inasistencia'`, `dias=0`, `habiles=false` y `activo=true`.
    - En el frontend: etiqueta "Inasistencia a cita" en el panel de alertas y en la configuración.
      Va en `TIPOS_SIN_DIAS`, y la alerta muestra al paciente y enlaza a su ficha como las de
      control.

## Componentes

1. **Migración 1360** (o la siguiente libre cuando se implemente; la Fase 1 usa 1350): agrega las
   columnas de la decisión 1 a `cita`, con su índice único y la FK, y pone `origen='SIGE'` en las
   filas existentes.
2. **`app/services/salutem_sync/citas_cepa.py`**: la correspondencia de estados (función pura y
   testeable), la resolución de paciente, ingreso y profesional en lote (consultas `IN` en lotes de
   500, por el límite de 1000 de Oracle), el upsert por `salutem_cita_id`, la eliminación por
   desaparición o por quedar fuera de ventana, y la auditoría con actor `sistema:salutem-sync`.
3. **Orquestador**: el paso nuevo, con su conteo en la bitácora del sync: creadas, actualizadas,
   eliminadas, omitidas por estado desconocido, citas de pacientes del CEPA sin ingreso en
   ventana, y `agendada` con más de 90 días (decisión 6b).
4. **Configuración**: `CITAS_SALUTEM_DESDE` (fecha, por defecto 2026-01-01) y
   `CITAS_ESPECIALIDADES_REPORTES` (CSV, por defecto vacío). Ambas se documentan en `.env.example`.
5. **Reportes**: un filtro común en `reportes_filtros` (solo `origen='SALUTEM'` y las
   especialidades configuradas) que aplican los 5 consumidores. Ojo: adherencia filtra por
   `Cita.ingreso_id` sin hacer join con `Ingreso`, así que el filtro tiene que funcionar solo
   sobre las columnas de `cita`. Además, adherencia con el nuevo
   denominador y carga agrupada por `cita.profesional_nombre` (decisión 11).
6. **`PATCH /citas/{id}/estado`**: responde 409 para las filas SALUTEM.
7. **Seed de desarrollo**: las citas se crean con `origen='SALUTEM'`.
8. **Alertas**: la corrección de `_construir_hitos_control_medico` y la autorresolución
   (decisión 12); el tipo `INASISTENCIA`, su creación en el paso de citas, la fila de
   `config_alerta` en la migración, y las etiquetas y el enlace en el frontend (decisión 13).

## Errores y bordes
- Si una persona de SALUTEM cruza con dos pacientes (un RUT duplicado en el SIGE), la cita se
  omite y se registra un aviso. No se adivina a cuál pertenece.
- Si cambia la fecha de una cita, se vuelve a calcular su ingreso. Si deja de caer en una
  ventana, se elimina.
- Si el paciente es un borrador sin ingreso (pendiente de folio), sus citas no se importan hasta
  que se le registre el folio. Como el ingreso nuevo dispara la revisión (decisión 6), en ese
  momento entran sus citas pasadas.
- Si el sync está caído, los reportes quedan desactualizados, pero no rotos.
- Todo el SQL debe ser portable: sin `DISTINCT ON`, con `true()`/`false()` de Core y el
  `TRIM` de Core.

## Pruebas
- La correspondencia de estados: los 9 estados, más uno desconocido y uno nulo.
- La importación:
  - cruce por RUT y por `salutem_persona_id`;
  - una cita dentro y otra fuera de la ventana;
  - dos ingresos que contienen la fecha (gana el más reciente);
  - un cambio de estado que actualiza la fila;
  - una cita desaparecida que borra la fila;
  - un ingreso nuevo que trae citas pasadas;
  - una cita anterior a `CITAS_SALUTEM_DESDE` que no se importa;
  - la idempotencia (correr dos veces no crea duplicados).
- La resolución de `profesional_id` por nombre, también con espacios sobrantes.
- Los reportes: solo cuentan `origen='SALUTEM'`, el filtro de especialidades funciona, el nuevo
  denominador de adherencia (las anuladas no cuentan) y la carga agrupada por `cita.profesional_nombre`.
- El PATCH sobre una fila SALUTEM responde 409, y sobre una fila SIGE responde 200.
- El modo `backfill` del orquestador incluye el paso nuevo.
- Alerta de control médico:
  - Un control SALUTEM vencido cuyo paciente tiene hora vigente no genera alerta.
  - Un control SALUTEM con `proximo_agendado = true` y sin hora vigente sí la genera.
  - Un control CEPA con `proximo_agendado = true` no la genera.
  - Una alerta abierta se resuelve sola cuando aparece la hora.
  - Un ingreso cerrado no genera alerta.
- Alerta de inasistencia:
  - Se crea al importar una cita NO_ASISTE de los últimos 14 días; no se crea si es más antigua.
  - No se duplica al volver a correr el sync.
  - No se crea si el tipo está desactivado.
  - No se crea para una especialidad fuera del filtro.
  - Se resuelve cuando aparece una hora vigente.

## Fuera de alcance
- Hora de la cita, sucursal y financiador. El JSON los trae y se pueden agregar después.
- Escribir en SALUTEM.
- Mostrar las citas en la ficha del paciente, porque ya existe la pestaña SALUTEM.

## Preguntas abiertas para el CEPA

Están ordenadas por cuánto cambian los números de los reportes. Cada una indica qué se hace si no
hay respuesta.

1. **P1 — ¿Qué atenciones cuentan como "cita" para los reportes?** ¿Todas las especialidades
   (médico, psicología, EPT, evaluación de ingreso, gestión administrativa…) o solo algunas?
   *Por defecto: todas. Se puede acotar después sin reimportar.*
2. **P2 — ¿Cómo se calcula la adherencia?** ¿Las horas anuladas cuentan como incumplidas? ¿Y las
   horas agendadas que todavía no ocurren? *Por defecto: adherencia = atendidas / (atendidas +
   inasistencias). Las anuladas y las futuras no cuentan.*
3. **P3 — ¿Desde qué fecha quieren el historial?** *Por defecto: desde el 1 de enero de 2026.*
4. **P4 — Las citas que hoy existen en el SIGE (creadas al confirmar propuestas de agenda), ¿son
   de prueba y se pueden borrar?** *Por defecto: se conservan, pero los reportes no las cuentan.*
5. **P5 — En el reporte de carga, ¿un paciente cuenta para el profesional que lo atendió en cada
   cita, o para su profesional asignado en el ingreso?** *Por defecto: para quien atendió.*
6. **P6 — Las horas que caen fuera del período del ingreso (por ejemplo, una evaluación antes de
   la fecha de ingreso), ¿deben contarse?** *Por defecto: no.*
7. **P7 — En SALUTEM, ¿qué significa "Recepcionado"?** ¿El paciente llegó (y por lo tanto la
   cita se puede contar como realizada aunque no aparezca "Atendido") o es solo un paso intermedio?
   *Por defecto: se cuenta como agendada hasta que SALUTEM informe "Atendido" o "No asiste".*
8. **P8 — Cuando un paciente no llega a su hora, ¿quién debe recibir el aviso para volver a
   contactarlo?** ¿Las administrativas, Coordinación, el profesional que lo iba a atender o
   todos? ¿Quieren el aviso para todas las especialidades o solo para algunas? *Por defecto:
   aparece en el panel general de alertas, que ven Coordinación y las administrativas, para las
   mismas especialidades que cuentan en los reportes.*
