# Pendientes para completar el sistema — septiembre 2026

**Origen:** revisión del sistema desplegado en la VM UTalca (`segicepa-dev.utalca.cl`,
192.168.22.183, Oracle 19c), 25-09-2026, cruzada con el código de `main` al commit `0650fb3`
(PR #32).
**Antecedentes:** [`01-decisiones-v5.md`](./01-decisiones-v5.md) (preguntas abiertas PA-v5-01…06),
[`BUGS-revision-2026-08.md`](./BUGS-revision-2026-08.md) (defectos de la revisión de agosto) y
[`00-decisiones-v4.md`](./00-decisiones-v4.md) (D1–D15).

## Propósito

Reunir en un solo lugar **todo lo que falta para que la contraparte (CEPA, Pilar García) perciba
el sistema como completo**, y separarlo según quién tiene que moverse:

- **Grupo A — Defectos y cabos sueltos visibles en la app.** Los resolvemos nosotros, sin esperar
  a nadie. Primero los callejones sin salida: botones que no hacen nada y textos que dicen
  "pendiente".
- **Grupo B — Historias bloqueadas por respuestas de la contraparte.** Cada ticket trae la
  pregunta **redactada para enviársela a Pilar**, la historia que desbloquea y lo que hay hoy con
  valor provisorio.
- **Grupo C — Dependencias externas** (DTI, FabricApp, IMED, Meta/WhatsApp). Cada ticket dice qué
  pedir exactamente y qué se habilita al recibirlo.
- **Grupo D — Operación y datos.** Trabajo interno sobre la VM y los datos, sin impacto visible
  pero con riesgo si se posterga.

Los IDs usan el prefijo `COMP-2609-NN`. Las historias de origen se citan por su ID `CEPA-XXX`; este
documento **no las reemplaza**: registra el hueco entre lo que exigen y lo que hay desplegado.

> **Criterio de prioridad.** **Alta** = el usuario lo ve y se topa con él (botón muerto, texto de
> "pendiente", dato que falta en pantalla) o hay un riesgo con datos personales. **Media** = el
> hueco existe pero el usuario no lo ve de inmediato (contrato de API, regla que debería ser
> configurable). **Baja** = fuera de v1 o sin impacto hasta que un tercero responda.

## Resumen

| ID | Título | Tipo | Módulo | Prioridad | Bloqueado por |
|----|--------|------|--------|-----------|---------------|
| COMP-2609-01 | "Ayuda y soporte" y el ícono (?) no hacen nada | Defecto | Shell | Alta | — |
| COMP-2609-02 | "Configuración" del menú lateral no hace nada | Defecto | Shell | Alta | — |
| COMP-2609-03 | Indicadores del Topbar: "— activos" fijo y "críticas" mal contado | Defecto | Shell | Alta | — |
| COMP-2609-04 | Listado de licencias muestra "—" en Folio LM, Reposo, GAF e ISL | Defecto | Licencias | Alta | — |
| COMP-2609-05 | Pestaña "Observaciones" de la ficha dice "pendiente (ciclo futuro)" | Decisión pendiente | Ingresos | Alta | Respuesta de Pilar |
| COMP-2609-06 | El job de alertas no está programado | Defecto | Alertas | Alta | — |
| COMP-2609-07 | Umbrales de alerta fijos en el código | Defecto | Alertas / Licencias | Media | PA-v5-04 (solo el valor) |
| COMP-2609-08 | Vista 360 de la API devuelve fármacos, licencias, controles y reintegro vacíos | Defecto | API / Ingresos | Media | — |
| COMP-2609-09 | Mostrar las atenciones de SALUTEM dentro de Controles médicos | Historia (**resuelta 25-09**) | Controles | Alta | PA-v5-06 (parcial) |
| COMP-2609-10 | Reglas del folio por programa | Decisión pendiente | Ingresos | Media | PA-v5-01 |
| COMP-2609-11 | Catálogos de tipo de ingreso y tipo de derivación | Decisión pendiente | Ingresos | Alta | PA-v5-02 |
| COMP-2609-12 | Tramos de GAF | Decisión pendiente (**catálogo provisorio implementado 25-09**) | Controles / Licencias | Alta | PA-v5-03 (solo confirmar la segmentación) |
| COMP-2609-13 | Umbrales y textos de las alertas de licencias y fármacos | Decisión pendiente | Alertas | Media | PA-v5-04 |
| COMP-2609-14 | Planilla Excel de casos EPT | Decisión pendiente | EPT | Media | PA-v5-05 |
| COMP-2609-15 | Origen del resumen de controles | Decisión pendiente | Controles | Media | PA-v5-06 |
| COMP-2609-16 | Desarrollo de la sigla NPE | Decisión pendiente | Reintegro / Controles | Baja | Respuesta de Pilar |
| COMP-2609-17 | "Detalles de la ficha" comprometidos por la contraparte | Decisión pendiente | Ingresos | Media | Respuesta de Pilar |
| COMP-2609-18 | Ejemplo numérico de referencia para la adherencia | Decisión pendiente | Reportería | Media | Respuesta de Pilar |
| COMP-2609-19 | Carga masiva de casos EPT desde Excel | Historia | EPT | Media | COMP-2609-14 |
| COMP-2609-20 | Alerta por tramo de GAF en licencia médica | Historia (**implementada desactivada 25-09**) | Licencias / Alertas | Media | COMP-2609-13 (solo el umbral y el texto) |
| COMP-2609-21 | Activar el servidor de QA | Dependencia externa | Plataforma | Alta | DTI |
| COMP-2609-22 | SSO institucional seguro (SAML o validación del token huemul) | Dependencia externa | Autenticación | Alta | DTI |
| COMP-2609-23 | Servidor SMTP institucional para alertas por correo | Dependencia externa | Alertas | Media | DTI (PA6) |
| COMP-2609-24 | API key de producción de SALUTEM | Dependencia externa | Integración SALUTEM | Alta | FabricApp |
| COMP-2609-25 | Confirmar si la agenda de SALUTEM es consultable por API | Dependencia externa | Agendamiento | Media | FabricApp |
| COMP-2609-26 | Anonimizar SALUTEM QA (hoy trae identidades reales) | Dependencia externa | Integración SALUTEM | Alta | FabricApp |
| COMP-2609-27 | Integración IMED (P2, construida y apagada) | Dependencia externa | API | Baja | CEPA (PA5) + IMED |
| COMP-2609-28 | WhatsApp como canal de alertas (fuera de v1) | Dependencia externa | Alertas | Baja | CEPA + Meta (WABA) |
| COMP-2609-29 | Purgar de la VM la copia de SALUTEM y el ingreso de prueba con RUT real | Operación | Datos / VM | Alta | — |
| COMP-2609-30 | Migración de los ~846 registros históricos | Operación | Ingresos | Media | PA7 + planilla limpia |
| COMP-2609-31 | Cifrado y retención de datos de salud mental | Operación | Plataforma | Media | PA3 (DTI / Mario) |

## Ya resuelto en esta revisión

Tres cabos sueltos detectados en la misma revisión ya están en `main` y **no** se abren como
ticket:

- **Buscador lateral "Buscar…" sin efecto** — PR #30 (`ca117dd`). Con Enter lleva a Ingresos con el
  término (`?q=`) y busca por RUT, folio, nombre o ID SALUTEM (`Sidebar.tsx:27-33`).
- **Pestaña Fármacos de un ingreso nuevo mostraba "No se pudieron cargar las recetas"** — PR #32
  (`6745903`). Sin registro farmacológico el listado responde `[]` en vez de 404.
- **Mensajes de validación en inglés en "Nuevo ingreso"** ("Number must be greater than or equal
  to 1") — PR #31 (`30aeb50`). Campo vacío dice "Requerido" y la edad explica el rango.

---

# Grupo A — Defectos y cabos sueltos visibles en la app

## [COMP-2609-01] "Ayuda y soporte" y el ícono (?) no hacen nada

**Tipo:** Defecto · **Módulo:** Shell (`frontend/src/components/shell`) · **Prioridad:** Alta
**Justificación:** está en todas las pantallas; es el primer lugar donde un usuario nuevo busca
ayuda y hoy no responde.
**Historias relacionadas:** v4 D13 (manual de usuario y capacitación).

**Contexto**
- `Sidebar.tsx:165-173` — el botón "Ayuda y soporte" es un `<button>` sin `onClick` ni enlace.
- `Topbar.tsx:64-66` — el ícono `HelpCircle` (?) es un `<button>` sin `onClick` ni `title`.
- Ya existe un **portal de incidencias** para la contraparte:
  `https://cepa-incidencias.dramirez-gysactiva.chatgpt.site` (alimenta la tabla *Incidencias* en
  Airtable).

**Resultado observado:** clic en cualquiera de los dos no produce ningún efecto.
**Resultado esperado:** ambos abren la misma ayuda: una página (`/ayuda`) o un modal con
(a) el manual de uso o sus secciones principales, y (b) un enlace visible al portal de incidencias
para reportar un problema.

**Criterios de aceptación**
- [ ] "Ayuda y soporte" (menú lateral) y el ícono (?) (Topbar) abren el mismo destino.
- [ ] El destino muestra el manual de uso (contenido mínimo: cómo buscar un paciente, crear un
      ingreso, registrar licencia/control, dónde ver alertas) o enlaza a él.
- [ ] Hay un enlace "Reportar un problema" al portal de incidencias, que abre en pestaña nueva.
- [ ] El ícono (?) tiene `title`/`aria-label` ("Ayuda").
- [ ] Con el menú colapsado, el botón sigue funcionando y tiene tooltip.
- [ ] Test de componente: clic en cada botón muestra la ayuda.

**Verificación de cierre**
- [ ] En la VM, con perfil Administrativo, ambos botones llevan a la ayuda y el enlace al portal
      abre el formulario de incidencias.
- [ ] Ningún botón del shell queda sin acción (revisión con `grep` de `<button` sin `onClick`
      en `components/shell/`).

---

## [COMP-2609-02] "Configuración" del menú lateral no hace nada

**Tipo:** Defecto · **Módulo:** Shell · **Prioridad:** Alta
**Justificación:** botón muerto visible en todas las pantallas, justo al lado de "Ayuda".
**Historias relacionadas:** `CEPA-002` (usuarios y roles), `CEPA-110` (formularios dinámicos),
`CEPA-096` (ventanas de proceso), `CEPA-100` RN-3 / v5 D21 (umbrales parametrizables).

**Contexto**
- `Sidebar.tsx:174-182` — botón "Configuración" sin `onClick`.
- Las pantallas de configuración ya existen y están en la sección "Administración" del menú
  (`app/shell/nav.ts:74-95`): `/usuarios` y `/config-formularios` (solo Coordinación) y
  `/ventanas-proceso` (todos los perfiles).

**Resultado observado:** clic sin efecto.
**Resultado esperado:** una de dos, a decidir en el refinamiento:
1. **Navegar** a un índice de configuración que liste, según rol, las pantallas existentes
   (usuarios, formularios dinámicos, ventanas de proceso) y, cuando exista, la de umbrales de
   alerta (`COMP-2609-07`); o
2. **Esconder** el botón, dado que "Administración" ya da acceso a las mismas pantallas.

**Criterios de aceptación**
- [ ] El botón navega a un destino útil **o** deja de mostrarse. No queda un botón sin acción.
- [ ] Si navega: el índice respeta RBAC (Administrativo y Auditor no ven usuarios ni formularios;
      un acceso directo a esas rutas sigue denegado).
- [ ] Si se esconde: no quedan referencias a "Configuración" en el shell.

**Verificación de cierre**
- [ ] Probado en la VM con los tres perfiles (Coordinación, Administrativo, Auditor).

---

## [COMP-2609-03] Indicadores del Topbar: "— activos" fijo y "críticas" mal contado

**Tipo:** Defecto · **Módulo:** Shell · **Prioridad:** Alta
**Justificación:** el guion permanente se lee como "el sistema no sabe cuántos pacientes tiene",
en la parte más visible de todas las pantallas.
**Historias relacionadas:** `CEPA-090` (dashboard), `CEPA-101` (panel de notificaciones).

**Contexto**
- `Topbar.tsx:50-54` — la píldora verde muestra el literal `— activos`; el comentario dice
  *"placeholder count until Dashboard module provides it"*. El módulo Dashboard ya existe, pero
  `ResumenDashboard` (`backend/app/schemas/reportes.py:20-31`) no expone un conteo de ingresos
  activos.
- `AppShell.tsx:35` y `:47` — la píldora roja "N críticas" cuenta **todas** las alertas en estado
  `pendiente`, no solo las críticas.

**Resultado observado:** "— activos" en todas las pantallas; "críticas" infla el número.
**Resultado esperado:** "N activos" = ingresos con `estado = activo` (`EstadoCaso.ACTIVO`); la
píldora roja cuenta solo lo que su rótulo dice, o cambia el rótulo a "pendientes".

**Criterios de aceptación**
- [ ] El backend expone el conteo de ingresos activos (campo nuevo en `GET /dashboard` o endpoint
      liviano de conteo), respetando RBAC de lectura.
- [ ] La píldora muestra el número real y se actualiza al crear o cerrar un ingreso.
- [ ] Mientras carga, muestra un estado de carga, no un guion permanente; si falla, oculta la
      píldora en vez de mostrar un valor falso.
- [ ] La píldora roja cuenta alertas críticas (definir criterio: vencidas o de plazo perentorio) o
      se rotula "pendientes".
- [ ] Clic en "N activos" lleva al listado de Ingresos filtrado por activos (deseable).

**Verificación de cierre**
- [ ] En la VM, el número coincide con `SELECT COUNT(*) FROM ingreso WHERE estado = 'activo'`.

---

## [COMP-2609-04] Listado de licencias muestra "—" en Folio LM, Reposo, GAF e ISL

**Tipo:** Defecto · **Módulo:** Licencias médicas (`frontend/src/features/licencias`) ·
**Prioridad:** Alta
**Estado:** resuelta en código el 25-09-2026 (rama `claude/lote2-licencias-vista360`, pendiente de
despliegue). El historial por folio trae `folio_lm`, `tipo_reposo`, `eeag_gaf`, `envio_isl` e
`ingreso_id` en cada fila, y la respuesta trae el `ingreso_id` del folio; la pantalla ya no pide
el detalle por fila.
**Justificación:** es el listado de trabajo diario de Licencias; cuatro columnas en guion hacen
parecer que los datos no se guardaron (el mismo síntoma que motivó `BUG-2608-03`).
**Historias relacionadas:** `CEPA-070`, `CEPA-073`, `CEPA-074`.

**Contexto**
- `LicenciasPage.tsx:116-120` — Folio LM, Reposo, GAF/EEAG e ISL se muestran como "—" hasta que
  llega el detalle de cada fila. Comentario en el código: *"backend contract gap: slim has no
  tipo_reposo/eeag_gaf/envio_isl"*.
- `LicenciasPage.tsx:237-238` — por cada licencia del listado se hace **una petición de detalle
  adicional** (`useLicenciasDetalle`): N+1 llamadas.
- `LicenciasPage.tsx:251-259` — los filtros Reposo e ISL **dejan pasar** las filas cuyo detalle
  aún no llega (`if (full && …)`): mientras carga, el filtro muestra resultados que no cumplen.
- `LicenciasPage.tsx:240-242` — el `ingreso_id` se deduce del primer detalle cargado porque la
  respuesta del listado no lo trae.

**Resultado observado:** columnas en "—" al abrir el listado; filtros Reposo/ISL imprecisos
mientras cargan; una petición por fila.
**Resultado esperado:** el listado trae en una sola respuesta todos los campos que muestra.

**Criterios de aceptación**
- [ ] El esquema del historial (`LicenciaReadSlim` o equivalente) incluye `folio_lm`,
      `tipo_reposo`, `eeag_gaf` y `envio_isl`; la respuesta del listado incluye `ingreso_id`.
- [ ] `LicenciasPage` deja de pedir el detalle por fila.
- [ ] Los filtros Reposo e ISL se aplican sobre datos completos desde el primer render.
- [ ] Test de API del listado con los campos nuevos; test de componente sin llamadas de detalle.
- [ ] Tipos del frontend regenerados (`types/api.ts`).

**Verificación de cierre**
- [ ] En la VM, un paciente con 3 o más licencias muestra las cuatro columnas completas al primer
      render y la pestaña de red registra una sola llamada al listado.

---

## [COMP-2609-05] Pestaña "Observaciones" de la ficha dice "pendiente (ciclo futuro)"

**Tipo:** Decisión pendiente · **Módulo:** Ingresos (ficha del paciente) · **Prioridad:** Alta
**Justificación:** es el único texto de la app que le dice al usuario, literalmente, que algo
está sin terminar; no hay ninguna historia del backlog que lo respalde.
**Historias relacionadas:** ninguna. Ni el PRD ni v4/v5 piden un módulo de observaciones en la
ficha (las `observaciones` que existen son campos de licencia, `CEPA-073` RN-1).

**Contexto**
- `PatientSheet.tsx:404` declara la pestaña; `PatientSheet.tsx:554-564` muestra "Sin
  observaciones registradas." y *"Módulo de observaciones clínicas — pendiente (ciclo futuro)"*.
- Por v4 D1 el sistema **no** registra información clínica: eso vive en SALUTEM. Unas
  "observaciones clínicas" contradirían esa decisión.

**Pregunta para Pilar** (para enviar tal cual):
> En la ficha del paciente hay una pestaña "Observaciones". ¿Necesitan un espacio para dejar notas
> administrativas sobre el caso (por ejemplo, "se llamó al empleador", "paciente pide cambio de
> horario")? Si es así: ¿quién puede escribirlas (administrativos, coordinación), deben poder
> editarse o borrarse, y el auditor debe verlas? Las notas clínicas seguirían en SALUTEM.

**Resultado esperado**
- **Si la respuesta es sí:** historia nueva de **observaciones administrativas** en EPIC-01: texto
  libre, autor y fecha automáticos, orden cronológico, sin edición (o edición auditada), registro
  en el log de auditoría (`CEPA-003`), lectura para Auditor.
- **Si es no:** se retira la pestaña.
- **Mientras no haya respuesta:** se quita el texto "pendiente (ciclo futuro)". Un usuario no debe
  leer que falta un módulo.

**Criterios de aceptación**
- [ ] La pregunta se envió a Pilar y la respuesta quedó registrada en este ticket.
- [ ] Ninguna pantalla muestra "pendiente (ciclo futuro)" ni textos equivalentes (revisar con
      `grep -ri "pendiente\|ciclo futuro" frontend/src`).
- [ ] Si se implementa: cada observación registra autor y fecha y queda en el log de auditoría;
      Auditor solo lectura (TC de permisos).

**Verificación de cierre**
- [ ] En la VM, la pestaña no existe o funciona de punta a punta.

---

## [COMP-2609-06] El job de alertas no está programado

**Tipo:** Defecto · **Módulo:** Alertas y notificaciones · **Prioridad:** Alta
**Justificación:** si nadie aprieta un botón, no aparece ninguna alerta nueva, y el panel de
alertas es una de las funcionalidades que más pidió la contraparte (v5 D21).
**Historias relacionadas:** `CEPA-100` RN-2 (job de revisión periódica), `CEPA-072`, `CEPA-022`.

**Contexto**
- El motor (`backend/app/services/alertas.py:445`, `ejecutar_job_alertas`) solo se invoca desde
  `POST /api/v1/alertas/ejecutar-job` (`routers/alertas.py:30-44`) y desde `seed_dev_data`.
  Ninguna pantalla llama a ese endpoint.
- Las alertas de licencias (`licencias_alerta.py`) se generan con el botón "Generar alertas" de
  `LicenciasPage.tsx:337-376`; el docstring del endpoint dice *"El job automático diario lo
  invocará desde EPIC-10"* (`routers/licencias.py:65-66`), y eso no ocurrió.
- `ops/vm/crontab-salutem-sync.txt` solo programa el sync de SALUTEM. No hay entrada de cron para
  alertas en el repo. **No verificado en el crontab real de la VM.**

**Resultado observado:** las alertas de ODAS, EPT, ISL, recetas, controles y consentimiento solo
aparecen si alguien dispara el job a mano.
**Resultado esperado:** el job corre solo, al menos una vez al día hábil, sin intervención.

**Criterios de aceptación**
- [ ] Script `ops/vm/run-alertas.sh` + entrada de crontab (mismo patrón que el sync de SALUTEM:
      `flock`, log a archivo) que ejecuta el motor y la generación de alertas de licencias y
      recetas.
- [ ] Idempotente: correrlo dos veces el mismo día no duplica alertas (ya lo es por diseño;
      cubrir con test).
- [ ] La traza de auditoría registra `actor = sistema`.
- [ ] El runbook de `docs/operacion/` documenta instalación y reversión.
- [ ] Decidir si el botón "Generar alertas" de Licencias se conserva (útil para probar) o se retira.

**Verificación de cierre**
- [ ] En la VM, al día siguiente de instalar el cron, `alerta_notif` tiene filas nuevas con
      `actor = sistema` y el log del job muestra la ejecución.

---

## [COMP-2609-07] Umbrales de alerta fijos en el código

**Tipo:** Defecto · **Módulo:** Alertas / Licencias · **Prioridad:** Media
**Justificación:** el usuario no lo ve hasta que pide cambiar un plazo; entonces requiere un
despliegue, justo lo que v5 D21 prohíbe.
**Historias relacionadas:** `CEPA-072` RN-1 y `TC-072-07`, `CEPA-100` RN-3, v5 D21.

**Contexto**
- `backend/app/services/licencias_alerta.py:47` — `umbral_habiles: int = 3` como parámetro por
  defecto; el endpoint (`routers/licencias.py:68`) nunca pasa otro valor.
- `backend/app/services/alertas.py:177-185` — `VENTANAS_DEFAULT` fija en código las ventanas de
  todas las alertas del motor (licencia 3 hábiles, EPT 5, ISL 5, receta 5, ODA 7, control 7,
  consentimiento 30).
- `CEPA-072` RN-1: *"El umbral es parametrizable por Coordinación (v5 D21), no una constante del
  código"*. `TC-072-07` exige que el cambio aplique sin redespliegue.
- Los festivos tampoco son configurables: `contar_dias_habiles` recibe `festivos` pero nadie se
  los pasa, así que solo excluye sábados y domingos.

**Resultado observado:** cambiar cualquier umbral exige editar código y desplegar.
**Resultado esperado:** Coordinación edita los umbrales (y el calendario de festivos) desde la
interfaz; el job los lee en cada ejecución.

**Criterios de aceptación**
- [ ] Tabla de configuración de alertas (tipo, días, hábiles sí/no, texto del mensaje) sembrada
      con los valores actuales, marcados como provisorios hasta `COMP-2609-13`.
- [ ] Pantalla de edición solo para Coordinación, auditada.
- [ ] `licencias_alerta.py` y `alertas.py` leen la configuración, no constantes.
- [ ] Festivos chilenos configurables y usados en el cálculo de días hábiles.
- [ ] `TC-072-07` automatizado: cambiar de 3 a 5 días cambia el resultado del job sin reiniciar.

**Verificación de cierre**
- [ ] En la VM, Coordinación cambia el umbral de licencias y la siguiente ejecución del job
      (`COMP-2609-06`) lo respeta.

---

## [COMP-2609-08] Vista 360 de la API devuelve fármacos, licencias, controles y reintegro vacíos

**Tipo:** Defecto · **Módulo:** API / Ingresos · **Prioridad:** Media
**Estado:** decisión **opción 1 (completar)**, resuelta en código el 25-09-2026 (rama
`claude/lote2-licencias-vista360`, pendiente de despliegue). `licencias` usa `LicenciaRead`,
`controles` `ControlMedicoRead`, `reintegro` `CasoReintegroRead` y `farmacos` el registro
farmacológico de cada ingreso con su esquema de indicaciones (historial completo, con `vigente`) y
sus recetas. Una consulta por dimensión filtrada por los ingresos del paciente.
**Justificación:** no se ve en pantalla (la ficha carga cada módulo por separado), pero la API
promete un dato que no entrega, y es la API que consumirán terceros (EPIC-12).
**Historias relacionadas:** `CEPA-012` CA-1 y RN-3, `CEPA-120`.

**Contexto**
- `backend/app/services/busqueda.py:85-99` — `vista_360` solo consulta los ingresos y devuelve
  `farmacos`, `licencias`, `controles` y `reintegro` como listas vacías fijas (docstring:
  *"Otras dimensiones quedan como ranuras"*).
- `backend/app/schemas/busqueda.py:18-21` — esos campos son `list[Any] = []`: el Swagger no
  documenta su forma.
- En el frontend, `useVista360` se usa en Ingresos, Fármacos, Controles, EPT y Reintegro solo para
  obtener paciente e ingresos (p. ej. `ControlesPage.tsx:364-365`). Ninguna pantalla lee las otras
  dimensiones, así que **retirar el endpoint no es opción**; lo que se decide es qué hacer con los
  cuatro campos.

**Resultado observado:** `GET /api/v1/pacientes/{id}/vista-360` responde `"licencias": []` aunque
el paciente tenga licencias.
**Resultado esperado:** una de dos:
1. **Completar:** las cuatro dimensiones se llenan con esquemas tipados y se cumple
   `CEPA-012` RN-2 (< 2 s); o
2. **Retirar los campos** del esquema y documentar que la vista 360 de la API devuelve paciente +
   ingresos, y que cada dimensión se consulta en su endpoint.

**Criterios de aceptación**
- [ ] Decisión tomada y registrada aquí.
- [ ] Ningún campo del esquema devuelve una lista vacía fija.
- [ ] Los campos que queden tienen esquema Pydantic tipado (no `Any`) y aparecen en Swagger.
- [ ] Test de API: paciente con una licencia y un control los ve en la vista 360 (opción 1), o el
      esquema ya no tiene esos campos (opción 2).

**Verificación de cierre**
- [ ] En la VM, la respuesta para un paciente con datos en todos los módulos coincide con lo que
      muestra la ficha.

---

## [COMP-2609-09] Mostrar las atenciones de SALUTEM dentro de Controles médicos

**Tipo:** Historia · **Módulo:** Controles médicos · **Prioridad:** Alta
**Estado:** **resuelta el 25-09-2026** (PRs #33, #35, #36 y #37, desplegados en la VM). Cada
atención **Médico/a** atendida de SALUTEM se crea sola como control médico con la etiqueta
SALUTEM: fecha, médico, semana, próximo control (la siguiente cita vigente), licencia, tipo de
reposo, GAF (número o tramo) y evolución. La RECA la completa el CEPA y el sync no la toca. Las
demás especialidades quedan en la pestaña SALUTEM de la ficha. Los criterios de abajo quedan
como referencia de lo pedido.
**Historias relacionadas:** `CEPA-060`, `CEPA-062`, `CEPA-121`; responde en parte PA-v5-06
(`COMP-2609-15`).

El sync de SALUTEM ya copia citas y atenciones a la VM (`salutem_cita`, `salutem_atencion`), y la
ficha las muestra en la pestaña SALUTEM. Falta que el módulo Controles médicos las presente junto a
los controles registrados en SIGE, para que el administrativo no tenga que cruzar dos pantallas.

**Criterios de aceptación**
- [ ] Controles médicos muestra, por paciente, las atenciones de SALUTEM (fecha, profesional,
      estado) diferenciadas visualmente de los controles de SIGE.
- [ ] Solo lectura: nada se escribe en SALUTEM (v4 D12).
- [ ] Con la integración deshabilitada o sin datos, un estado vacío explica por qué.
- [ ] No se muestran datos de personas fuera de la lista permitida mientras rija
      `SALUTEM_SYNC_PERSONAS_PERMITIDAS` (ver `COMP-2609-26`).

---

# Grupo B — Historias bloqueadas por respuestas de la contraparte

> Las preguntas están redactadas para enviarse a Pilar sin editar. Al final del documento hay un
> **borrador de correo** que las reúne. Todos los valores provisorios de este grupo son **nuestros,
> no acordados**: no deben presentarse a la contraparte como definitivos.

## [COMP-2609-10] Reglas del folio por programa (PA-v5-01)

**Tipo:** Decisión pendiente · **Prioridad:** Media · **Desbloquea:** `CEPA-011` (v5 D16)
**Justificación:** hoy el folio funciona; lo que falta es que respete el formato de cada programa.

**Pregunta para Pilar**
> Cada programa maneja sus folios internos. ¿Nos pueden enviar el formato de folio de cada programa
> (por ejemplo, prefijo, año, número correlativo) con uno o dos ejemplos reales? ¿La numeración es
> independiente por programa o hay una sola numeración para todo el CEPA? Si dos programas llegan
> al mismo número, ¿es un error o es válido?

**Implementado hoy (provisorio)**
- Folio automático `F-<año>-<correlativo de 4 dígitos>`, único y **global por año**
  (`backend/app/services/folio.py:4` y `:38`).
- Opción de folio manual (`Ingreso.folio_manual`, `models/ingreso.py:44`); el folio no se puede
  editar después de creado (`schemas/ingreso.py:70`).

**Al recibir la respuesta:** formato por programa, validación del folio manual contra ese formato
y exposición de la regla en el formulario (D16).

---

## [COMP-2609-11] Catálogos de tipo de ingreso y tipo de derivación (PA-v5-02)

**Tipo:** Decisión pendiente · **Prioridad:** Alta · **Desbloquea:** `CEPA-010` RN-6, `CEPA-017`
**Justificación:** el tipo de ingreso aparece en el formulario principal, en filtros y en
reportería; si el catálogo es incorrecto, lo ve en cada ingreso que registra.

**Pregunta para Pilar**
> En el formulario de ingreso manejamos dos listas: "tipo de derivación" (DIEP, DIAT, PAPT a flujo
> AT, Reingreso FUMP, Reingreso SUSESO, Convenio U.Clínica, Proyecto, Particular, PAPT) y "tipo de
> ingreso" (la lista que nos envió en agosto: DIEP, DIEP sin EPT, DIAT, Flujo PAPT, Reingreso FUPM,
> Reingreso SUSESO, Reingreso ISL, Convenio, Proyecto, Consulta espontánea, Derivación otro
> prestador). ¿Son dos datos distintos o es el mismo? ¿Se escribe FUMP o FUPM? ¿"Particular" y
> "Consulta espontánea" son lo mismo? ¿"Convenio U.Clínica" y "Convenio" son lo mismo?

**Implementado hoy (provisorio)**
- `TipoDerivacion` con el catálogo v4 D4 (`backend/app/domain/enums.py:10-21`).
- `TipoIngreso` con **cuatro valores** (consulta espontánea, convenio, proyecto, particular —
  `enums.py:24-30`).
- **Hueco detectado:** la decisión provisoria de v5 D17 (adoptar el catálogo v5 para
  `tipo de ingreso`) **no está reflejada en el código**. Aunque Pilar no responda, conviene aplicar
  el catálogo v5 como provisorio, para que la contraparte vea sus propios valores.

**Al recibir la respuesta:** catálogo definitivo, migración de los valores ya cargados y ajuste de
filtros de reportería (`CEPA-051` CHG-04, `CEPA-095` CHG-08).

---

## [COMP-2609-12] Tramos de GAF (PA-v5-03)

**Tipo:** Decisión pendiente · **Prioridad:** Alta ·
**Desbloquea:** `CEPA-062` RN-3, `CEPA-073` RN-1, `CEPA-075`
**Justificación:** Pilar corrigió explícitamente el modelo del GAF (v5 D18) y el sistema sigue
pidiendo un número; lo notará en cuanto registre un control o una licencia.

**Pregunta para Pilar**
> Nos indicó que el GAF se registra como un tramo (por ejemplo, 11-20%). ¿Cuál es la lista
> completa de tramos que usa el CEPA? ¿Es la escala estándar de 10 en 10 (1-10, 11-20, …, 91-100)
> o tienen una segmentación propia?

**Implementado hoy (provisorio)**
- **D18 no está implementado.** El GAF sigue siendo un entero libre:
  `control_medico.gaf` (`models/control_medico.py:64`) y `licencia_medica.eeag_gaf`
  (`models/licencia.py:60`). No existe la tabla `gaf_tramo`.
- v5 D18 permite avanzar sin la respuesta: catálogo parametrizable sembrado con los tramos EEAG de
  10 en 10, marcado como provisorio. **Recomendación:** hacerlo ya, junto con la migración de los
  enteros cargados al tramo que los contiene.

**Novedad (25-09-2026):** los formularios de SALUTEM ya registran el GAF por tramo, con opciones
de 10 en 10 (en el ambiente de pruebas aparecen `41-50`, `51-60` y `61-70`). Desde el PR #37 los
controles creados desde SALUTEM guardan ese tramo en `control_medico.gaf_tramo` y la tabla de
Controles lo muestra. Es un buen indicio de que la escala es la estándar de 10 en 10, pero hay que
confirmarlo con Pilar. Los controles y licencias cargados en SIGE siguen pidiendo un número.

**Estado:** catálogo provisorio implementado el 25-09-2026 (rama `claude/lote4-gaf-tramos`,
migración `1300`). Tabla `gaf_tramo` (desde, hasta, etiqueta, orden, activo, provisorio) sembrada
con los 10 tramos EEAG de 10 en 10, marcados `provisorio`; `GET /api/v1/gaf-tramos` para los tres
roles; helper `tramo_que_contiene()` en `backend/app/domain/gaf.py`. Los formularios de GAF
(Licencia/RECA del control y envío ISL de la licencia) eligen el tramo de un select; se guarda en
`control_medico.gaf_tramo` y en la nueva `licencia_medica.eeag_gaf_tramo`. Los enteros se
conservan y la migración rellenó el tramo de las filas que ya tenían entero (un 0 no cae en ningún
tramo y queda como entero). Las tablas de Controles y Licencias muestran el tramo, o el entero si
no hay tramo. **Sigue pendiente** la confirmación de Pilar (PA-v5-03).

**Al recibir la respuesta:** ajustar el catálogo sembrado (y quitar la marca `provisorio`); si
cambia la segmentación, remapear los datos migrados.

---

## [COMP-2609-13] Umbrales y textos de las alertas de licencias y fármacos (PA-v5-04)

**Tipo:** Decisión pendiente · **Prioridad:** Media ·
**Desbloquea:** `CEPA-072` RN-1/RN-1c, `CEPA-075`, reglas de alerta de EPIC-02 (`CEPA-022`)

**Pregunta para Pilar**
> Para las alertas de licencias médicas: ¿con cuántos días de anticipación al vencimiento quieren
> el aviso? ¿Las licencias de reposo parcial se avisan distinto (antes, después, a otra persona)?
> ¿Qué texto debería leer el administrativo en la alerta? Para fármacos: ¿qué situación debe
> generar un aviso (receta por vencer, cambio de esquema, otra)?

**Implementado hoy (provisorio):** licencias a 3 días hábiles, sin distinción por reposo parcial
(`licencias_alerta.py:47`); recetas a 5 días corridos (`alertas.py:181`). Los textos son los
genéricos del motor.

**Al recibir la respuesta:** cargar los valores en la configuración de `COMP-2609-07` (no en
código) y aplicar la regla de reposo parcial.

---

## [COMP-2609-14] Planilla Excel de casos EPT (PA-v5-05)

**Tipo:** Decisión pendiente · **Prioridad:** Media · **Desbloquea:** `COMP-2609-19` (`CEPA-033`)

**Pregunta para Pilar**
> En la revisión de agosto nos ofreció enviar la planilla Excel con los casos EPT. ¿Nos la puede
> enviar? Nos basta con una copia con los datos personales reemplazados por datos ficticios,
> siempre que conserve las columnas, los formatos y algunos casos representativos.

**Implementado hoy:** carga uno a uno desde la pantalla EPT (`CEPA-030`). No hay carga masiva.
`backend/app/domain/enums_ept.py:14` cita un "Excel de origen" para algunos catálogos, pero no hay
lector de planillas.

---

## [COMP-2609-15] Origen del resumen de controles (PA-v5-06)

**Tipo:** Decisión pendiente · **Prioridad:** Media · **Desbloquea:** `CEPA-062` (panel derecho)

**Pregunta para Pilar**
> En Controles médicos, el resumen del lado derecho: ¿debe mostrar lo que ya está en la ficha de
> SALUTEM (lo traeríamos automáticamente) o prefieren que el administrativo escriba un comentario
> propio? Pueden ser ambas cosas.

**Implementado hoy:** el resumen se arma con los controles registrados en SIGE. `COMP-2609-09`
(resuelta el 25-09) crea los controles desde las atenciones Médico/a de SALUTEM, con la evolución
como observación, lo que cubre la primera alternativa.
La segunda parte de PA-v5-06 ("¿qué es ingreso ID?") se trató como defecto (`BUG-2608-07`).

---

## [COMP-2609-16] Desarrollo de la sigla NPE

**Tipo:** Decisión pendiente · **Prioridad:** Baja · **Afecta:** `CEPA-041` RN-1b, `CEPA-062`
RN-5b (v5 D20)

**Pregunta para Pilar**
> En el tipo de RECA incluimos EP, EC, AT, AC, NPE y "No aplica". ¿Qué significa NPE? Lo
> queremos mostrar completo en la ayuda del campo.

**Implementado hoy:** el catálogo D20 está desplegado (verificado en la VM el 15-09-2026, ver
`BUG-2608-02`); NPE se muestra solo como sigla.

---

## [COMP-2609-17] "Detalles de la ficha" comprometidos por la contraparte

**Tipo:** Decisión pendiente · **Prioridad:** Media · **Afecta:** `CEPA-010`, `CEPA-110`

**Pregunta para Pilar**
> En su correo del 27-08 nos comentó que nos enviaría detalles adicionales de la ficha del
> paciente. ¿Los tiene disponibles? Si le acomoda, podemos revisarlos juntos en una reunión corta.

**Implementado hoy:** la ficha con los campos del PRD y v4/v5, editable desde el 15-09-2026
(`BUG-2608-01`). Los campos adicionales pueden agregarse como campos configurables (`CEPA-110`) sin
cambiar código.

---

## [COMP-2609-18] Ejemplo numérico de referencia para la adherencia (CEPA-095)

**Tipo:** Decisión pendiente · **Prioridad:** Media · **Desbloquea:** publicación de la métrica
de `CEPA-095` (QA de métricas, v4 D5)

**Pregunta para Pilar**
> Para validar el indicador de adherencia necesitamos un caso de ejemplo resuelto por ustedes: un
> paciente (o un mes de un programa) con cuántas citas agendadas y cuántas realizadas, y el
> porcentaje que ustedes esperan ver. ¿Las citas anuladas por el CEPA y las reagendadas cuentan
> como agendadas?

**Implementado hoy:** `% adherencia = realizadas / agendadas × 100`
(`backend/app/services/adherencia.py:9-16`), con `None` si no hay citas agendadas. No hay un caso
de referencia validado por la contraparte.

---

## [COMP-2609-19] Carga masiva de casos EPT desde Excel

**Tipo:** Historia · **Módulo:** EPT · **Prioridad:** Media · **Bloqueado por:** `COMP-2609-14`
**Historia de origen:** `CEPA-033` (P1, v5 D22)

No construida. El alcance está definido en `CEPA-033`: validación previa, vinculación por folio,
reporte de errores por fila y carga atómica o por filas válidas (a decidir). Se estima y se agenda
en cuanto llegue la planilla; sin ella, el mapeo de columnas sería una suposición.

**Criterios de aceptación mínimos:** los de `CEPA-033`, más un test con la planilla real
anonimizada como fixture.

---

## [COMP-2609-20] Alerta por tramo de GAF en licencia médica

**Tipo:** Historia · **Módulo:** Licencias / Alertas · **Prioridad:** Media ·
**Bloqueado por:** `COMP-2609-12` (tramos) y `COMP-2609-13` (qué tramos alertan)
**Historia de origen:** `CEPA-075` (P0, v5)

**Estado:** implementada **desactivada** el 25-09-2026 (rama `claude/lote4-gaf-tramos`,
migración `1300`). Es un tipo más del motor (`gaf_licencia` en `config_alerta`): el job diario
genera una alerta in-app por licencia no anulada cuyo tramo de GAF está **en o bajo** un tramo
umbral (si la licencia solo tiene el entero, se usa el tramo que lo contiene). Idempotente (una
alerta activa por licencia) y registrada en auditoría con actor sistema. Coordinación la activa y
elige el tramo umbral en `/config-alertas`, sin redespliegue (CA-3).

Decisiones provisorias: se sembró **desactivada** para respetar `CEPA-075` RN-2 (sin criterio de la
contraparte no se alerta); el umbral sembrado es `21-30` (tramos 1-10, 11-20 y 21-30), solo como
valor inicial al activarla. El criterio es "en o bajo un tramo" y no un conjunto arbitrario de
tramos: cubre el caso clínico esperado (alertar el mayor deterioro funcional) con la configuración
existente. El texto del mensaje es el genérico del motor.

**Al recibir la respuesta (`COMP-2609-13`):** cargar el tramo umbral y activarla desde
`/config-alertas`; si Pilar define un conjunto no contiguo de tramos alertables, cambiar el umbral
por una marca por tramo en `gaf_tramo`.

---

# Grupo C — Dependencias externas

## [COMP-2609-21] Activar el servidor de QA

**Responsable externo:** DTI UTalca (Mario Seguel) · **Prioridad:** Alta
**Qué pedir:** el servidor de QA con su esquema Oracle, acceso SSH para el usuario de despliegue,
nombre DNS y fecha estimada. Confirmar si el procedimiento es igual al de DEV
(`srv-segicepa-dev`).
**Qué se habilita:** separar la VM de pruebas de la contraparte del ambiente de desarrollo; activar
el SSO (DTI indicó el 05-08-2026 que el SSO solo se conecta en QA); aplicar `ENTORNO=qa`, con lo
que el acceso huemul `sin_verificar` deja de estar permitido.

## [COMP-2609-22] SSO institucional seguro (SAML o validación del token huemul)

**Responsable externo:** DTI UTalca · **Prioridad:** Alta
**Contexto:** el SP SAML está implementado y *fail-closed* (`backend/app/auth/saml/sp.py`; sin
`SAML_IDP_CERT` no autentica). El acceso vía huemul (`backend/app/auth/sso/`) funciona solo en
modo `sin_verificar`, que el código respeta únicamente con `ENTORNO=dev`
(`backend/app/config.py:52-58`): huemul devuelve `v=1` constante y no hay nada que verificar.
**Qué pedir (una de dos):**
1. Registrar el SP de SIGE en el IdP `idprovider.utalca.cl` (entity ID y ACS en `config.py:41-42`)
   y confirmar el nombre del atributo que trae el RUT; o
2. Documentar cómo validar contra UTalca el token que devuelve huemul (endpoint, parámetros,
   respuesta).
**Qué se habilita:** login institucional en QA/producción con identidad verificable.

## [COMP-2609-23] Servidor SMTP institucional para alertas por correo

**Responsable externo:** DTI UTalca · **Prioridad:** Media · **Pregunta:** PA6
**Qué pedir:** host, puerto, TLS, credenciales de una casilla de servicio (sugerida
`cepa-alertas@utalca.cl`, `config.py:80`) y si hay límite de envíos por hora.
**Qué se habilita:** `CEPA-102`. El código ya degrada de forma controlada sin SMTP
(`config.py:73-80`); basta configurar las variables en la VM y probar.

## [COMP-2609-24] API key de producción de SALUTEM

**Responsable externo:** FabricApp · **Prioridad:** Alta
**Qué pedir:** API key y URL base del ambiente de **producción** para la empresa CEPA, límites de
tasa de la API (hoy el sync se autolimita a 2 llamadas/s, `config.py:98-99`) y un contacto
técnico para incidentes.
**Qué se habilita:** que el sync lea pacientes reales en producción; hoy solo hay credenciales de
QA (correo de FabricApp del 02-09-2026).

## [COMP-2609-25] Confirmar si la agenda de SALUTEM es consultable por API

**Responsable externo:** FabricApp · **Prioridad:** Media
**Qué pedir:** si la API expone la agenda (horas disponibles y citas futuras por profesional), con
un ejemplo de respuesta.
**Qué se habilita:** la respuesta a Pilar sobre vincular el agendamiento con SALUTEM (v5, sección
"Preguntas de la contraparte que ya podemos responder") y la precisión de `CEPA-080`. Si la
agenda no está expuesta, la respuesta a Pilar cambia a "no por ahora" y hay que decírselo.

## [COMP-2609-26] Anonimizar SALUTEM QA (hoy trae identidades reales)

**Responsable externo:** FabricApp · **Prioridad:** Alta
**Contexto:** el ambiente QA de SALUTEM contiene identidades reales de pacientes. Como mitigación,
el sync se limita a una lista de personas permitidas (`SALUTEM_SYNC_PERSONAS_PERMITIDAS`,
`config.py:102-106`) y no busca por RUT cuando hay lista (`services/salutem_sync/filtro.py:43`).
**Qué pedir:** que QA se anonimice (o se reemplace por pacientes ficticios) y confirmar por escrito
cuándo quedó hecho.
**Qué se habilita:** probar el sync completo sin lista blanca y sin exponer datos de salud de
personas reales en ambientes de desarrollo. Relacionado con `COMP-2609-29`.

## [COMP-2609-27] Integración IMED (P2, construida y apagada)

**Responsable externo:** CEPA (decisión, PA5) y luego IMED (credenciales) · **Prioridad:** Baja
**Contexto:** `CEPA-122` está construida detrás del flag `IMED_ENABLED=false` (`config.py:109`);
con el flag apagado el endpoint responde 503 "pendiente de habilitación (PA5)".
**Qué pedir:** a la contraparte, si IMED entra en v1; si entra, a IMED, credenciales y el formato
real de licencias y recetas electrónicas.
**Qué se habilita:** encender el flag tras validar el contrato con datos reales.

## [COMP-2609-28] WhatsApp como canal de alertas (fuera de v1)

**Responsable externo:** CEPA (decisión y cuenta) + Meta (WhatsApp Business API) ·
**Prioridad:** Baja
**Contexto:** fuera de alcance en v1 por falta de cuenta WABA (EPIC-10, `CEPA-102` RN-5). No hay
código.
**Qué pedir:** solo si la contraparte lo reactiva: número institucional, cuenta de WhatsApp
Business verificada y plantillas aprobadas por Meta.
**Qué se habilita:** un canal adicional del motor de alertas.

---

# Grupo D — Operación y datos (interno)

## [COMP-2609-29] Purgar de la VM la copia de SALUTEM y el ingreso de prueba con RUT real

**Tipo:** Operación · **Prioridad:** Alta
**Justificación:** son datos de salud de personas reales en un ambiente de desarrollo; es un
riesgo que no depende de nadie más para cerrarse.

**Contexto**
- Las tablas `salutem_persona`, `salutem_cita` y `salutem_atencion`
  (`backend/app/models/salutem_copia.py:30-50`) en el esquema `UTCEPA01` de la VM contienen una
  copia de pacientes reales traída de SALUTEM QA antes de que existiera la lista de personas
  permitidas.
- El ingreso de prueba **F-2026-0061** se creó con un RUT real y tiene **4 fichas SALUTEM**
  asociadas.

**Criterios de aceptación**
- [ ] Antes de borrar: registrar solo **conteos** por tabla (no exportar filas; un respaldo de
      datos personales es justo lo que se quiere eliminar).
- [ ] Borrar las filas de `salutem_atencion`, `salutem_cita` y `salutem_persona` que no
      correspondan a personas de la lista permitida, respetando el orden de claves foráneas.
- [ ] Borrar el ingreso F-2026-0061, sus 4 fichas y sus registros dependientes; revisar si el
      paciente asociado queda huérfano y borrarlo.
- [ ] Revisar `audit_log` y los logs del sync en `~/sige-cepa/logs/` por RUT o nombres de esas
      personas y decidir su tratamiento.
- [ ] Confirmar que `SALUTEM_SYNC_PERSONAS_PERMITIDAS` está configurada en el `.env` de la VM para
      que el próximo sync no las vuelva a traer.
- [ ] Dejar constancia (fecha, quién, conteos antes y después) en este ticket, sin datos
      personales.

## [COMP-2609-30] Migración de los ~846 registros históricos (PA7)

**Tipo:** Operación · **Prioridad:** Media · **Bloqueado por:** PA7 y la planilla fuente limpia
**Contexto:** la hoja Excel "Ingresos" (846+ registros, 27 columnas) es la que reemplaza EPIC-01.
`CEPA-010` advierte que puede arrastrar RUT y folios no estándar (PA7). Sin la migración, el
sistema arranca vacío y el dashboard no refleja la operación real del CEPA.

**Criterios de aceptación**
- [ ] Mapeo columna a campo acordado con la contraparte, incluidos los catálogos de
      `COMP-2609-11` y `COMP-2609-12`.
- [ ] Script de migración idempotente con reporte de filas rechazadas y motivo (RUT inválido,
      folio duplicado, catálogo desconocido).
- [ ] Ensayo completo en DEV/QA antes de producción; conteo final validado con Coordinación.
- [ ] Los folios históricos se cargan como folio manual (v4 D2) sin chocar con la secuencia
      automática.

## [COMP-2609-31] Cifrado y retención de datos de salud mental (PA3)

**Tipo:** Operación · **Prioridad:** Media · **Bloqueado por:** PA3 (DTI / Mario, v4 D13)
**Contexto:** `EPIC-00` y `EPIC-12` dejan abierta la política institucional de cifrado, retención
y anonimización. Hoy el contenido de `FichaClinica` e `ImedPayload` se guarda como JSON sin cifrado
de columna, y el log de auditoría no tiene política de retención.

**Qué pedir a DTI:** si la normativa institucional exige cifrado en reposo más allá del de Oracle,
plazos de retención del log y de los datos clínicos copiados de SALUTEM, y criterio de
anonimización para ambientes no productivos.

**Criterios de aceptación**
- [ ] Respuesta de DTI registrada.
- [ ] Si se exige cifrado de columna: aplicado a `FichaClinica.contenido`, `ImedPayload` y la
      copia de SALUTEM, sin cambiar los esquemas de la API.
- [ ] Política de retención implementada como job programado (mismo mecanismo que
      `COMP-2609-06`) y documentada.

---

## Anexo — Borrador de correo a Pilar García

> Asunto: SIGE — preguntas pendientes para cerrar el sistema
>
> Hola Pilar:
>
> Estamos cerrando los últimos detalles de SIGE y tenemos algunas preguntas que solo el CEPA puede
> responder. Mientras tanto, el sistema funciona con valores provisorios que ajustaremos según sus
> respuestas.
>
> 1. **Folio:** ¿nos puede enviar el formato de folio de cada programa, con un ejemplo? ¿La
>    numeración es independiente por programa o es una sola para el CEPA?
> 2. **Tipo de ingreso y tipo de derivación:** ¿son dos datos distintos o es el mismo? ¿Se
>    escribe FUMP o FUPM? ¿"Particular" es lo mismo que "Consulta espontánea"? ¿"Convenio
>    U.Clínica" es lo mismo que "Convenio"?
> 3. **GAF:** ¿cuál es la lista completa de tramos? ¿De 10 en 10 (1-10 … 91-100) u otra?
> 4. **Alertas de licencias:** ¿con cuántos días de anticipación quieren el aviso? ¿El reposo
>    parcial se avisa distinto? ¿Qué texto debería decir? **Fármacos:** ¿qué situación debe
>    generar un aviso?
> 5. **EPT:** ¿nos puede enviar la planilla Excel de casos EPT? Nos sirve con los datos personales
>    reemplazados por ficticios.
> 6. **Resumen de controles:** ¿debe mostrar lo que ya está en la ficha de SALUTEM, un comentario
>    del administrativo o ambos?
> 7. **NPE:** ¿qué significa esta sigla en el tipo de RECA?
> 8. **Detalles de la ficha:** ¿tiene disponibles los detalles que comentó en su correo del 27-08?
> 9. **Adherencia:** ¿nos puede dar un caso de ejemplo con citas agendadas, citas realizadas y el
>    porcentaje que esperan ver? ¿Las citas anuladas o reagendadas cuentan como agendadas?
> 10. **Observaciones:** en la ficha del paciente hay una pestaña "Observaciones". ¿Necesitan
>     notas administrativas sobre el caso? Si es así, ¿quién las escribe y quién las puede ver?
>
> Si le acomoda, podemos revisarlas en una reunión corta.
>
> Saludos,
