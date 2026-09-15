# Decisiones de la revisión v5 — ambiente de pruebas SIGE-CEPA (agosto 2026)

> Cambios de alcance, reglas de negocio y defectos derivados del documento
> `Revisión etapa preliminar SIGE.docx` (María del Pilar García Zerene, Encargada de Riesgos
> Psicosociales, CEPA — recibido el **27-08-2026**). Transcripción completa del documento en
> [`../feedback/2026-08-27-revision-etapa-preliminar-sige.md`](../feedback/2026-08-27-revision-etapa-preliminar-sige.md).
>
> A diferencia de la revisión v4 (revisión del **PRD**), esta revisión se hizo **operando el
> ambiente de pruebas**: mezcla requisitos nuevos, correcciones a decisiones ya cerradas y
> **defectos observados en la aplicación**. Los defectos viven en
> [`BUGS-revision-2026-08.md`](./BUGS-revision-2026-08.md), no aquí.
>
> **Estado:** las decisiones **D16–D22** están incorporadas en las historias del backlog. Las
> **preguntas abiertas PA-v5-01 … PA-v5-06** bloquean definición y están pendientes de respuesta
> de la contraparte CEPA.

## Índice

| Ref | Tipo | Título | Impacto |
|-----|------|--------|---------|
| D16 | Cambio | Folio manual por programa y reglas del folio | CEPA-011 |
| D17 | **Conflicto con v4 D4** | `tipo de ingreso` es un campo distinto de `tipo de derivación` | CEPA-010, CEPA-017 (nueva) |
| D18 | **Conflicto con v4 D8** | El GAF es un **rango entre dos porcentajes**, no un entero 0–100 | CEPA-062, CEPA-073 |
| D19 | Nuevo | Marca "Fármacos al ingreso" (SI/NO) con detalle | CEPA-018 (nueva) |
| D20 | Cierra pregunta abierta | Catálogo de tipo de RECA: EP · EC · AT · AC · NPE · No aplica | CEPA-041, CEPA-062 |
| D21 | Cambio transversal | Ninguna alerta se implementa sin su regla escrita y parametrizada | EPIC-10 y todas las historias con alerta |
| D22 | Nuevo | Carga de casos EPT vinculada a folio, con carga masiva desde Excel | CEPA-033 (nueva) |
| PA-v5-01 … 06 | Pregunta abierta | Ver sección final | — |

---

## D16. Folio manual por programa y reglas explícitas del folio
- La revisión v4 (D2) ya habilitó el folio manual para reingresos, folios pre-asignados e
  ingresos posteriores a las 15:00. La revisión v5 **amplía el motivo**: *"cada programa maneja
  sus folios internos"*, por lo que la opción manual es **de uso corriente**, no una excepción.
- Se exige además **escribir las reglas del folio** (formato, prefijo, secuencia, unicidad,
  colisión) y exponerlas en la interfaz, no solo en el backlog.
- **Impacto:** `CEPA-011` — la opción de folio manual deja de presentarse como excepción; se
  agrega la regla de folio por programa y la exposición del formato al usuario.
- **Dependencia:** el formato exacto por programa es **PA-v5-01**.

## D17. `tipo de ingreso` es un campo distinto de `tipo de derivación` — catálogo en conflicto con v4 D4
- El formulario de nuevo ingreso debe incorporar **fecha de ingreso** y **tipo de ingreso**
  (desplegable), separado del `tipo de derivación` que ya modela `CEPA-010` (v4 D4).
- **El catálogo entregado en v5 no coincide con el de v4 D4:**

  | v4 D4 (`tipo de derivación`, vigente en CEPA-010) | v5 (`tipo de ingreso`, documento de Pilar) |
  |---|---|
  | DIEP | DIEP |
  | DIAT | DIAT |
  | PAPT a flujo AT | Flujo PAPT |
  | Reingreso FUMP | Reingreso FUPM |
  | Reingreso SUSESO | Reingreso SUSESO |
  | Convenio U.Clínica | Convenio |
  | Proyecto | Proyecto |
  | Particular | Consulta espontánea |
  | PAPT | — |
  | — | **DIEP sin EPT** *(nuevo)* |
  | — | **Reingreso ISL** *(nuevo)* |
  | — | **Derivación otro prestador** *(nuevo)* |

- Hay tres valores nuevos, dos discrepancias de nomenclatura que parecen erratas
  (**FUMP/FUPM**, **PAPT a flujo AT / Flujo PAPT**) y dos pares que pueden o no ser sinónimos
  (**Particular / Consulta espontánea**, **Convenio U.Clínica / Convenio**).
- **Decisión provisoria:** se adopta el catálogo v5 como valores de `tipo de ingreso` y se
  mantiene `tipo de derivación` con el catálogo v4 hasta que la contraparte confirme si son dos
  campos o uno solo mal nombrado. **Ambos catálogos quedan marcados como provisorios en el código
  y en las historias.**
- **Impacto:** `CEPA-010` (nota de conflicto en RN-6), `CEPA-017` (historia nueva).
- **Dependencia:** **PA-v5-02** — es una decisión de la contraparte, no nuestra.

## D18. El GAF es un rango entre dos porcentajes, no un entero 0–100
- La revisión v5 corrige: *"El GAF es un nivel entre dos valores porcentuales, por ejemplo:
  11-20%"*. El backlog v4 lo modela como **entero 0–100** (`CEPA-062` RN-3) y como **1–100**
  (`CEPA-073` RN-1, glosario EPIC-07): ambas definiciones quedan **obsoletas**.
- **Modelo nuevo:** el GAF se selecciona desde un **catálogo cerrado de tramos** (`gaf_tramo`),
  cada uno con `porcentaje_min` y `porcentaje_max` enteros, `min < max`, tramos contiguos y sin
  solapamiento. No se digita un número libre.
- **Impacto:** cambia modelo de datos, validación de formulario, TCs existentes
  (`TC-062-04`, `TC-073-05` dejan de ser válidos tal como están) y cualquier dato ya cargado
  como entero requiere migración.
- **Dependencia:** el listado exacto de tramos es **PA-v5-03**. Hasta tenerlo, se implementa el
  catálogo como tabla parametrizable y se siembra con los tramos estándar de la escala EEAG
  (1-10, 11-20, …, 91-100), a confirmar.

## D19. Marca "Fármacos al ingreso" (SI/NO) con detalle
- El documento lo pide dos veces (sección *Nuevo ingreso* y sección *Fármacos*): al registrar un
  ingreso debe indicarse si el paciente **llega con fármacos** y, si la respuesta es SÍ,
  especificar cuáles.
- Es un dato **del ingreso**, distinto del registro farmacológico de tratamiento que modela
  EPIC-02: describe la situación basal del paciente al entrar al CEPA.
- **Impacto:** `CEPA-018` (historia nueva en EPIC-01), con lectura desde EPIC-02.

## D20. Catálogo de tipo de RECA: EP · EC · AT · AC · NPE · No aplica
- El documento fija el desplegable de RECAS: **EP** (enfermedad profesional), **EC** (enfermedad
  común), **AT** (accidente del trabajo), **AC** (accidente común), **NPE**, **No aplica**.
- Esto **cierra la pregunta abierta** de `CEPA-041` ("confirmar catálogo de tipo de RECA") y da
  el catálogo que faltaba en `CEPA-062` (estado RECA).
- **Impacto:** `CEPA-041`, `CEPA-062`.
- **Pendiente menor:** confirmar el desarrollo de la sigla **NPE**, no explicitada en el documento.

## D21. Ninguna alerta se implementa sin su regla escrita y parametrizada
- El documento pregunta **cuatro veces** cómo se generan las alertas (licencias médicas, GAF,
  fármacos, remitido a ISL) y en todos los casos pide *"definir específicamente (regla)"*,
  *"crear reglas"*, *"incluir regla"*.
- **Decisión:** se adopta como criterio transversal — toda alerta del sistema debe declarar, en su
  historia y en configuración: **evento disparador, umbral, destinatario por rol, canal, texto del
  mensaje y condición de cierre**. Los umbrales son **parametrizables por Coordinación**, no
  constantes en el código.
- Alcanza a `CEPA-015` (ODAS), `CEPA-016` (consentimiento), `CEPA-022` (recetas), `CEPA-032`
  (plazos EPT), `CEPA-061` (próximo control), `CEPA-072` (vencimiento LM), `CEPA-075` (GAF, nueva),
  `CEPA-043` (remitido a ISL, nueva) y el motor `CEPA-100`.
- **Dependencia:** los umbrales concretos de licencias y fármacos son **PA-v5-04**.

## D22. Carga de casos EPT vinculada a folio, con carga masiva desde Excel
- La carga de un caso EPT debe **vincularse preferentemente al folio** del paciente, y el
  documento pregunta explícitamente si puede haber **carga manual / desde Excel** ofreciendo
  enviar la planilla.
- **Decisión:** se incorpora carga masiva desde Excel como historia P1, con validación previa y
  reporte de errores por fila. La vinculación por folio pasa a ser el camino primario de
  `CEPA-030`.
- **Impacto:** `CEPA-033` (historia nueva en EPIC-03).
- **Dependencia:** la planilla de referencia es **PA-v5-05**.

---

## Cambios aplicados a historias existentes

| Ref | Historia | Cambio |
|-----|----------|--------|
| CHG-01 | `CEPA-010` | Nota de conflicto de catálogo (D17); `tipo de ingreso` se separa de `tipo de derivación` |
| CHG-02 | `CEPA-011` | Folio manual por programa + regla de folio expuesta al usuario (D16) |
| CHG-03 | `CEPA-041` | Catálogo cerrado de tipo de RECA (D20); cierra pregunta abierta |
| CHG-04 | `CEPA-051` | Filtros ampliados: convenio, tipo de ingreso, mes/año de ingreso |
| CHG-05 | `CEPA-062` | GAF pasa a tramo (D18); estado RECA toma el catálogo D20 |
| CHG-06 | `CEPA-072` | Regla de alerta explícita: umbral parametrizable + caso de reposo parcial (D21) |
| CHG-07 | `CEPA-073` | GAF pasa a tramo (D18); glosario EPIC-07 actualizado |
| CHG-08 | `CEPA-095` | Adherencia segmentable además por convenio y tipo de ingreso |

## Historias nuevas

| ID | Épica | Título | Prioridad |
|----|-------|--------|-----------|
| `CEPA-017` | EPIC-01 | Fecha y tipo de ingreso en el formulario de nuevo ingreso | P0 |
| `CEPA-018` | EPIC-01 | Marca "Fármacos al ingreso" (SI/NO) con detalle | P0 |
| `CEPA-033` | EPIC-03 | Carga masiva de casos EPT desde Excel | P1 |
| `CEPA-043` | EPIC-04 | Alerta de caso remitido a ISL | P0 |
| `CEPA-074` | EPIC-07 | Filtros del listado de licencias médicas | P0 |
| `CEPA-075` | EPIC-07 | Alerta por tramo de GAF en licencia médica | P0 |

---

## Preguntas abiertas para la contraparte CEPA

> Estas seis preguntas **bloquean** la definición de reglas. Cada historia afectada queda
> implementada con la regla parametrizable y un valor por defecto explícitamente marcado como
> provisorio, para no detener el desarrollo — pero **ningún valor por defecto es acordado**.

- **PA-v5-01 — Reglas del folio (D16).** ¿Cuál es el formato del folio por programa (prefijo,
  año, secuencia)? ¿La secuencia es única global o por programa? ¿Qué pasa si dos programas
  emiten el mismo número? *Bloquea:* `CEPA-011`.
- **PA-v5-02 — Catálogo de tipo de ingreso (D17).** ¿`tipo de ingreso` y `tipo de derivación` son
  dos campos distintos o uno solo? Si son dos, ¿cuál es el catálogo definitivo de cada uno?
  ¿"Particular" y "Consulta espontánea" son el mismo valor? ¿"FUMP" o "FUPM"?
  *Bloquea:* `CEPA-010`, `CEPA-017`.
- **PA-v5-03 — Tramos de GAF (D18).** ¿Cuál es el listado completo de tramos válidos? ¿Se usa la
  escala EEAG estándar en tramos de 10 puntos (1-10 … 91-100) u otra segmentación propia del CEPA?
  *Bloquea:* `CEPA-062`, `CEPA-073`, `CEPA-075`.
- **PA-v5-04 — Umbrales de alerta (D21).** Para licencias: ¿cuántos días antes del vencimiento se
  alerta, y cuál es el tratamiento distinto del **reposo parcial**? ¿Cuál es el texto del mensaje
  para el usuario administrativo? Para fármacos: ¿qué evento dispara la alerta?
  *Bloquea:* `CEPA-072`, `CEPA-075`, y las reglas de alerta de EPIC-02.
- **PA-v5-05 — Planilla EPT (D22).** Pilar ofreció enviar el Excel de casos EPT; se requiere el
  archivo para fijar el mapeo de columnas y las validaciones de la carga masiva.
  *Bloquea:* `CEPA-033`.
- **PA-v5-06 — Origen del resumen de controles y significado de "ingreso ID".** Dos preguntas del
  documento sin respuesta posible desde nuestro lado:
  - *"En el resumen de controles, apartado a la derecha, ¿se verá lo que aparece en ficha o hay
    que dejar un comentario manual?"* — determina si ese panel se alimenta de SALUTEM (lectura vía
    API, EPIC-12) o es digitación del administrativo. *Bloquea:* `CEPA-062`.
  - *"¿A qué se refiere con ingreso ID? RUT, folio, nombre."* — es una pregunta **sobre nuestra
    interfaz**: el rótulo del campo no se entiende. Se renombra a un rótulo explícito en el
    formulario de licencias. *Ver:* `BUG-2608-07`.

## Preguntas de la contraparte que ya podemos responder

No todo lo que el documento pregunta requiere que la contraparte decida. Estas dos se responden
desde el diseño vigente y conviene contestarlas por escrito en lugar de dejarlas abiertas:

- **"¿El módulo de agendamiento puede vincularse con la agenda de SALUTEM?"** → **Sí en lectura,
  no en escritura.** El aplicativo puede leer la agenda vía la API de integración
  (`CEPA-121`) para proponer y contrastar horarios, pero **no escribe sobre SALUTEM** (v4 D12):
  la cita se crea en SALUTEM y el CEPA registra el estado `agendado sí/no` (`CEPA-061`).
  **Salvedad:** solo tenemos la API Key del ambiente **QA** (correo de FabricApp del 02-09-2026) y
  **aún no está verificado que la agenda esté entre los recursos que expone la API**. Confirmar
  con FabricApp antes de comprometer la funcionalidad. Detalle en `EPIC-08`.
- **"¿Se puede generar un indicador de adherencia general?"** → **Sí**, ya está en el backlog como
  `CEPA-095` (% adherencia = citas realizadas / citas agendadas, v4 D5). La revisión v5 agrega las
  segmentaciones por convenio y tipo de ingreso (CHG-08). Lo que sí falta es el **ejemplo numérico
  de referencia** que pidió la contraparte para validar el cálculo antes de publicar la métrica.

### Pendientes comprometidos por la contraparte
- **Detalles de la ficha** — Pilar los comprometió para la semana del 31-08-2026 (correo del
  27-08). **No se han recibido** al 04-09-2026.
- **Pacientes de prueba con atenciones simuladas** — disponibles en el ambiente del CEPA; Pilar
  ofrece generar más si se requieren para validar la integración SALUTEM.
