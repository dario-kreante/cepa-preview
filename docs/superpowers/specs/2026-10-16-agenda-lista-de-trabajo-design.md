# Diseño — Agendamiento como lista de trabajo ("Pacientes por citar")

> **Estado:** enfoque elegido en conversación el 2026-10-16 (opción A). El proceso concreto lo
> definió Claude a pedido del usuario y **se valida en el periodo de pruebas** con el CEPA; las
> decisiones marcadas *(hipótesis)* son las que esa validación debe confirmar o corregir.
> **Alcance:** solo lectura sobre SALUTEM (v4 D12). Reemplaza la pantalla Agenda y deja de usar
> las propuestas confirmables. Construye sobre los PR #49 (catálogo `profesional`) y #50
> (candidatos filtrados por profesional, `profesional.nombre = TRIM(medico_tratante)`). El 16-10
> se pidió quitar del #50 la parte que marca `proximo_agendado = true` al confirmar. Antes de
> empezar, hay que verificar que ese cambio ya esté en la rama.

## Objetivo

Que quien agenda en el CEPA abra el SIGE y vea **a quién tiene que citar, en qué orden y cuánta
carga le toca a cada día**, para después agendar la hora en **SALUTEM**, que es donde de verdad
viven las horas. El SIGE no reserva horas ni guarda una agenda paralela: arma la lista, registra
lo que pasó con cada llamada y saca al paciente de la lista cuando SALUTEM ya le tiene hora.

**Éxito:** un paciente con control vencido aparece en la lista del profesional que lo atiende; la
secretaría lo llama, le agenda hora en SALUTEM y, a lo más un ciclo de sync después (~5 min), el
paciente ya no está en la lista, sin que nadie tenga que "confirmar" nada en el SIGE.

## Por qué (lo que falla hoy)

La Agenda actual genera una "propuesta" de citas que se confirma en el SIGE. Esa confirmación no
llega a SALUTEM ni al paciente, no tiene hora, y crea dos agendas que no se hablan. Además:

- Se puede sobreagendar: dos propuestas del mismo período vuelven a traer a los mismos pacientes
  y el cupo no descuenta citas confirmadas en otras propuestas.
- `crear_disponibilidad` dice "crea o reemplaza" pero solo inserta: el mismo día queda duplicado y
  el scheduler toma el primero que encuentra.
- No considera feriados (la tabla `festivo` existe y la usan las alertas).
- Los pacientes que no caben en el cupo desaparecen sin rastro.
- Una propuesta queda `confirmada` con confirmar una sola cita; las demás quedan "propuesta"
  para siempre (los estados `descartada` existen pero nadie los usa).

## Hallazgos que condicionan el diseño

1. **`proximo_agendado` no sirve para cerrar el caso.** El sync lo calcula solo al vincular una
   atención ya realizada (`salutem_sync/controles.py::_campos` → `_proxima_cita`). Si la
   secretaría agenda la hora *después*, la cita llega a `salutem_cita` pero el control no se
   recalcula y `proximo_agendado` sigue en `false`. Por eso la lista debe mirar **`salutem_cita`
   directamente** para saber si el paciente ya tiene hora.
2. **Varios reportes dependen de la confirmación.** La tabla `cita` alimenta adherencia,
   operativo, convenio, carga y el dashboard (`routers/reporte_*.py`, `dashboard.py`). Hoy esa
   tabla solo se llena al confirmar propuestas (DD-1, `agendamiento/service.py::confirmar_citas`)
   o desde el seed. Si se quita la confirmación, esos reportes dejan de recibir citas nuevas hasta
   que `cita` se alimente desde SALUTEM (Fase 2).
3. **El cruce con SALUTEM es, sobre todo, por RUT.** `salutem_sync/filtro.cruce_con_paciente` une
   `Paciente.rut = SalutemPersona.rut` o, si existe, `paciente.salutem_persona_id`. Ese último
   campo solo lo llenan los pacientes borrador. Por eso la lista tiene que usar
   `cruce_con_paciente` y no solo `salutem_persona_id`.
4. **`proximo_agendado` queda viejo en los dos sentidos.** Si la hora se anula después de la
   vinculación, el campo sigue en `true`. No sirve ni para excluir ni para incluir a los
   pacientes que vienen de SALUTEM.

## Objetivos, no objetivos y anti-objetivos

**Objetivos**
- Lista priorizada por profesional con día sugerido según su cupo.
- Cierre automático cuando SALUTEM tiene una hora vigente futura para el paciente.
- Registro liviano de la gestión de contacto, para no llamar dos veces a la misma persona.
- Nadie desaparece en silencio: quienes no caben en el cupo o están en reposo se ven aparte.

**No objetivos**
- Reservar horas, manejar bloques horarios o escribir en SALUTEM.
- Notificar al paciente (correo, SMS).
- Reemplazar la agenda de SALUTEM.

**Anti-objetivos (sería un fracaso aunque funcione)**
- Que el SIGE vuelva a tener un estado "agendado" propio que pueda contradecir a SALUTEM.
- Que la secretaría tenga que marcar algo en el SIGE para que el paciente salga de la lista
  cuando ya lo agendó en SALUTEM (el registro de gestión es opcional, no un paso obligatorio).

## Decisiones

1. **Cálculo en vivo, sin persistir propuestas.** La lista se calcula en cada consulta con la
   lógica existente (`_cargar_candidatos` filtrado por profesional del PR #50 +
   `scheduler.proponer_agenda_semana`). No se crean filas de `propuesta_agenda` ni
   `cita_propuesta`.
2. **"Ya tiene hora" = existe una `salutem_cita` vigente con fecha ≥ hoy** para alguna
   `salutem_persona` que cruce con el paciente según `cruce_con_paciente` (RUT o
   `salutem_persona_id`). Vigente significa `desaparecida_en IS NULL` y `estado_id` fuera de
   (ANULADO, NO_ASISTE), el mismo criterio de `_proxima_cita`; conviene extraerlo a una función
   compartida.
   **Cómo se usa `proximo_agendado`** *(decisión de Claude)*: se ignora en los controles con
   `origen = 'SALUTEM'`, porque ahí manda `salutem_cita`. Se respeta solo en los controles que el
   CEPA carga a mano (`origen = 'CEPA'`), donde es lo único que indica que el paciente ya tiene
   hora. Así una hora anulada en SALUTEM devuelve al paciente a la lista.
   *(Hipótesis: cualquier hora futura del paciente cuenta, aunque no sea con el médico. La
   alternativa sería exigir una especialidad de control (`SALUTEM_ESPECIALIDADES_CONTROL`), pero
   `salutem_cita` no tiene una columna de especialidad, así que habría que leerla de `contenido`.
   Se valida en pruebas.)*
3. **Pacientes sin cruce con SALUTEM** (ninguna `salutem_persona` cumple `cruce_con_paciente`)
   se listan normalmente con la marca "sin vínculo SALUTEM", porque no se puede verificar si ya
   tienen hora.
3b. **Solo pacientes con ingreso activo** *(decisión de Claude)*. `_cargar_candidatos` hoy no
   filtra por `Ingreso.estado`. Se agrega el filtro `Ingreso.estado = activo` para no citar a
   pacientes egresados. Si el paciente tiene más de un ingreso activo, el folio que se muestra es
   el del más reciente.
4. **Feriados.** Los días de la tabla `festivo` no reciben carga (se pasan al scheduler como
   días sin cupo).
5. **Disponibilidad con reemplazo real.** `POST /disponibilidad-profesional` hace upsert por
   (profesional, día): si hay una fila activa para ese día, la reemplaza. Se agrega
   `DELETE /disponibilidad-profesional/{id}` (baja lógica, `activo=false`).
6. **Registro de gestión de contacto** (nuevo). Resultados posibles: `agendada_en_salutem`,
   `no_contesta`, `rechaza`, `otro`, más una nota opcional. Efecto en la lista:
   - `agendada_en_salutem` oculta al paciente por **3 días hábiles** *(hipótesis)*, que es el
     margen para que el sync traiga la hora. Si después de eso no aparece una hora en SALUTEM,
     el paciente vuelve a la lista con la marca "dijo agendada, sin hora en SALUTEM".
   - Los demás resultados no lo ocultan: se muestra el último contacto (fecha, resultado y
     usuario) en la fila.
   - *(Decisión de Claude)* El ocultamiento es por (paciente, profesional), porque se agendó con
     ese profesional. El "último contacto" que se muestra es el más reciente del paciente con
     cualquier profesional, porque una llamada es una llamada.
7. **Se retira la propuesta confirmable.** Sale de la UI y de la API la generación y la
   confirmación (`POST /propuestas-agenda`, `POST /propuestas-agenda/{id}/confirmar`). Las
   tablas `propuesta_agenda` y `cita_propuesta` y sus GET se mantienen por ahora como historial;
   se eliminan en una migración posterior, cuando la validación confirme el enfoque.
8. **Roles:** igual que hoy. Administrativo y Coordinación ven la lista y registran gestiones;
   Auditor solo lee.

## Componentes

### 1. Backend — lista calculada
`GET /api/v1/pacientes-por-citar?profesional_id=&desde=&hasta=` (por defecto, desde hoy hasta el
viernes de la semana siguiente). Respuesta:

- `por_dia`: lista de `{fecha, cupo, asignados}` para los días hábiles del rango.
- `pacientes`: cada uno con `paciente_id`, nombre, folio del ingreso activo, `prioridad`,
  `razon`, `fecha_objetivo` (el próximo control, o null si es por receta), `dia_sugerido`
  (null si no cupo), `seccion` (`por_citar` | `sin_cupo` | `en_reposo`), `reposo_hasta`,
  `sin_vinculo_salutem` y `ultima_gestion` ({fecha, resultado, usuario, nota} o null).

El cálculo vive en `agendamiento/service.py`. El scheduler puro solo cambia en dos cosas: recibe
el conjunto de feriados y devuelve también a los que no recibieron día (hoy se descartan sin
avisar).

### 2. Backend — gestión de contacto
Migración nueva con la tabla `gestion_citacion`: `id`, `paciente_id`, `profesional_id`,
`resultado` String(25), `nota` String(300) nullable, `usuario` String(60) y `created_at`.
Endpoints:
- `POST /api/v1/pacientes-por-citar/{paciente_id}/gestiones`
- `GET .../gestiones` (historial del paciente)

Cada alta queda en la auditoría.

### 3. Frontend — pantalla "Pacientes por citar" (reemplaza `/agenda`)
- Arriba: selector de profesional (catálogo, PR #49) y rango (esta semana / próximas 2 semanas /
  este mes).
- Una franja de carga por día, del tipo "Lun 14 · 3/4", donde los feriados aparecen como "Feriado".
- Una tabla "Por citar" ordenada por día sugerido y prioridad. Cada fila muestra: paciente y
  folio, badge de prioridad con la razón, fecha objetivo, día sugerido, último contacto y el botón
  "Registrar contacto" (un diálogo con el resultado y la nota).
- Secciones plegables "Sin cupo en el período" y "En reposo (hasta …)".
- La disponibilidad del profesional se mantiene en una tarjeta plegable con editar y quitar.
- El ítem del menú pasa a llamarse "Pacientes por citar" y la ruta se mantiene en `/agenda`.

### 4. Fase 2 — adherencia alimentada desde SALUTEM (PR aparte)
Hay que poblar `cita` desde `salutem_cita` para los pacientes vinculados (`cruce_con_paciente`) y
con ingreso en ventana (`vinculacion._en_ventana_del_ingreso`), usando esta correspondencia de
estados:

| `salutem_cita.estado_id` | `cita.estado` |
| --- | --- |
| ATENDIDO | `realizada` |
| NO_ASISTE | `inasistencia` |
| ANULADO | `anulada` |
| AGENDADO, AGENDADO_WEB, CONFIRMADO, CONFIRMADO_WEB, CONFIRMADO_EMAIL, RECEPCIONADO | `agendada` |

Requisitos: agregar a `cita` una columna `salutem_cita_id` para hacer upsert sin duplicar, y
hacer que el sync la mantenga al día. Hasta que esta fase esté lista, adherencia, operativo,
convenio, carga y el dashboard no reciben citas nuevas. Hay que decírselo al CEPA en las pruebas.

**Preguntas abiertas de la Fase 2.** Las deciden el CEPA y el usuario antes de planificar esa
fase:
- ¿Cuentan todas las especialidades de SALUTEM (psicología, EPT…) o solo las de control médico?
- ¿Las citas anuladas entran al denominador de adherencia? Hoy cuenta "agendadas" en cualquier
  estado.
- Qué hacer con las filas `cita` que ya crearon las confirmaciones del SIGE
  (`salutem_cita_id` nulo): borrarlas, mantenerlas o reconciliarlas, para que no se dupliquen.

## Errores y bordes
- Si el profesional no tiene disponibilidad, toda la lista cae en "Sin cupo" y la pantalla
  muestra un aviso para cargarla.
- Si `profesional_id` no existe o el profesional está inactivo, responde 404 o 422.
- Un mismo paciente puede tener varios ingresos: se usa el folio del ingreso activo más reciente.
- Si el sync de SALUTEM está caído, la lista sigue funcionando, pero el cierre automático se
  atrasa. Se puede mostrar la fecha del último sync exitoso (`salutem_sync_ejecucion`).

## Pruebas
- Scheduler: los feriados no reciben carga y los que no caben se devuelven en `sin_cupo`.
- Servicio: un paciente con `salutem_cita` vigente futura (cruzado por RUT y, por separado, por
  `salutem_persona_id`) no aparece; uno con la cita ANULADA o NO_ASISTE sí aparece, aunque su
  control SALUTEM tenga `proximo_agendado = true`; un control CEPA con `proximo_agendado = true`
  no aparece; un paciente sin cruce aparece con la marca correspondiente; un paciente egresado no
  aparece; el
  ocultamiento por `agendada_en_salutem` dura 3 días hábiles y después el paciente vuelve con la
  marca "dijo agendada, sin hora en SALUTEM".
- Disponibilidad: el upsert reemplaza en vez de duplicar.
- API: permisos por rol; la generación y la confirmación retiradas responden 404/405.
- Frontend: tests de hooks con MSW y de la pantalla (selector, secciones, diálogo de contacto).
- Que el SQL sea portable a Oracle 19c (D15): sin `DISTINCT ON` y con `true()`/`false()` de Core.

## A validar en el periodo de pruebas
- ¿Cualquier hora futura en SALUTEM cierra el caso, o solo una de control médico?
- ¿Tres días hábiles es un margen razonable para `agendada_en_salutem`?
- ¿Sirve la distribución por día (el cupo), o basta con la lista ordenada por prioridad?
- ¿Hacen falta otros resultados de contacto?
- ¿Un horizonte de dos semanas por defecto es el correcto?

## Qué queda en manos de quien construye
Los nombres internos, la forma exacta de los schemas, la extracción del criterio de vigencia a un
helper compartido, los textos de la UI (en español) y cómo se ordenan los commits, siempre que
las fases 1 (componentes 1 a 3) y 2 vayan en PRs separados.
