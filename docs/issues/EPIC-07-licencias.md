# EPIC-07 — Licencias Médicas

**Épica:** EPIC-07 — Licencias Médicas
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** §7.7
**Reemplaza:** hoja Excel «Licencias Médicas» (1.584+ registros, 15 columnas). Es el **módulo con mayor volumen de datos** del sistema; el diseño debe contemplar paginación e indexación desde el inicio (RNF rendimiento <2 s, PRD §9).

**Objetivo:** controlar el ciclo completo de la licencia médica (LM) de cada paciente — registro, cálculo automático de días acumulados, alertas de vencimiento y trazabilidad de envío al ISL — eliminando los cálculos manuales y la doble digitación.

**Perfiles operativos (v4 D1):** Coordinación, Administrativo, Auditor. **El perfil Clínico NO accede al sistema** (los clínicos registran en las fichas SALUTEM/SAM). Las alertas dirigidas a "médico tratante" del PRD §7.7.4 se reasignan al **administrativo asignado**.

**Historias:**
- [CEPA-070](#cepa-070-registro-de-licencia-médica) — Registro de licencia médica
- [CEPA-071](#cepa-071-cálculo-automático-de-días-acumulados-por-paciente) — Cálculo automático de días acumulados por paciente
- [CEPA-072](#cepa-072-alerta-de-vencimiento-de-licencia) — Alerta de vencimiento de licencia
- [CEPA-073](#cepa-073-trazabilidad-de-envío-a-isl-y-licencias-extra-sistema) — Trazabilidad de envío a ISL y licencias extra-sistema
- [CEPA-074](#cepa-074-filtros-del-listado-de-licencias-médicas) — Filtros del listado de licencias médicas *(v5)*
- [CEPA-075](#cepa-075-alerta-por-tramo-de-gaf-en-licencia-médica) — Alerta por tramo de GAF en licencia médica *(v5)*

### Glosario aplicable
| Término | Definición |
|---------|------------|
| **LM** | Licencia Médica. Tipos relevantes: **1** (enfermedad común), **5** (enfermedad/accidente del trabajo curativa), **6** (patología del embarazo / prórroga). |
| **ISL** | Instituto de Seguridad Laboral. Recibe el envío de las LM de casos de enfermedad/accidente laboral. |
| **GAF / EEAG** | Escala de Evaluación de la Actividad Global (Global Assessment of Functioning). **Se registra como un tramo entre dos porcentajes** (p. ej. `11-20%`), seleccionado de un catálogo cerrado (Decisiones v5 · D18). ~~Valor 1–100.~~ |
| **Reposo** | Período de descanso prescrito en la LM. **Total** (incapacidad completa) o **parcial** (media jornada / actividad reducida). |
| **77 BIS** | Art. 77 bis de la Ley 16.744: rechazo/recalificación de LM entre ISL y FONASA/ISAPRE. Una LM rechazada puede reasignarse de origen laboral a común (o viceversa). |
| **Licencia extra-sistema** | LM gestionada fuera del Sistema CEPA (papel / IMED / otra mutualidad) que igualmente debe registrarse para que el acumulado de días sea fidedigno (v4 D7). |

---

## [CEPA-070] Registro de licencia médica

**Épica:** EPIC-07 — Licencias Médicas
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.7.1
**Trazabilidad:** PRD §7.7.1 · Decisiones v4: D1, D8

### Historia
Como **Administrativo del CEPA**, quiero **registrar una licencia médica con todos sus datos vinculada al folio del paciente** para **dejar de transcribir las LM a la planilla Excel y mantener una fuente única y fidedigna por paciente**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo está en el formulario de nueva LM con un paciente seleccionado por RUT/folio
  - **Cuando** completa los campos obligatorios (región del paciente, nombre, RUT, folio de la LM, cantidad de días, fecha de inicio, fecha de término, tipo de reposo, tipo de LM, diagnóstico) y guarda
  - **Entonces** la LM queda registrada, vinculada al folio del paciente y visible en su historial de licencias
- **CA-2**
  - **Dado** que un administrativo ingresa una LM con fecha de término anterior a la fecha de inicio
  - **Cuando** intenta guardar
  - **Entonces** el sistema muestra un error de validación específico y no guarda, conservando los datos ya ingresados
- **CA-3**
  - **Dado** que el administrativo ingresa cantidad de días, inicio y fin del reposo (v4 D8)
  - **Cuando** la cantidad de días no coincide con la diferencia entre fechas de reposo
  - **Entonces** el sistema advierte de la inconsistencia antes de permitir el guardado
- **CA-4**
  - **Dado** un RUT con dígito verificador inválido
  - **Cuando** se intenta guardar la LM
  - **Entonces** el sistema bloquea el guardado con mensaje de RUT inválido

### Reglas de Negocio
- **RN-1:** Campos obligatorios §7.7.1: región del paciente, nombre, RUT (con validación de DV), folio de la LM, cantidad de días, fecha de inicio, fecha de término, tipo de reposo (total/parcial), tipo de LM (1, 5 o 6).
- **RN-2:** Campos adicionales obligatorios v4 D8: días de reposo, inicio del reposo, fecha de emisión, fin del reposo, indicación de reposo, diagnóstico.
- **RN-3:** `tipo_de_LM` solo admite valores del catálogo {1, 5, 6}. `tipo_de_reposo` solo admite {total, parcial}.
- **RN-4:** `fecha_termino ≥ fecha_inicio`; `fin_reposo ≥ inicio_reposo`; `fecha_emision ≤ fecha_inicio` (se emite antes o al inicio del reposo).
- **RN-5:** `cantidad_de_dias` debe ser coherente con (`fecha_termino − fecha_inicio + 1`); discrepancia genera advertencia bloqueante salvo confirmación explícita del administrativo (caso prórroga/empalme).
- **RN-6:** La LM se vincula al folio del paciente existente; no se crea LM sin folio asociado.
- **RN-7:** Toda operación CRUD se registra en el log de auditoría (quién, qué, cuándo) — PRD §7.13.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-070-01 | Positivo | Paciente con folio existente | Completar todos los campos obligatorios y guardar | RUT válido, días=15, inicio=01/06/2026, fin=15/06/2026, reposo total, tipo LM=1, dx=F32.1 | LM creada y visible en el historial del paciente; registrada en log de auditoría | Alta |
| TC-070-02 | Negativo | Formulario de nueva LM | Ingresar fin<inicio y guardar | inicio=15/06/2026, fin=01/06/2026 | Error de validación; no guarda; datos preservados | Alta |
| TC-070-03 | Negativo | Formulario de nueva LM | Ingresar RUT con DV incorrecto y guardar | RUT=12.345.678-0 (DV inválido) | Bloqueo con mensaje "RUT inválido" | Alta |
| TC-070-04 | Borde | Campos de reposo v4 D8 | Días=10 pero (fin_reposo−inicio_reposo+1)=12 | inconsistencia 10 vs 12 | Advertencia de inconsistencia antes de guardar (RN-5) | Media |
| TC-070-05 | Borde | Catálogo tipo LM | Intentar ingresar tipo LM=3 | tipo LM fuera de {1,5,6} | Rechazo: valor no permitido (RN-3) | Media |
| TC-070-06 | Permisos | Usuario perfil Auditor autenticado | Intentar abrir/guardar formulario de nueva LM | sesión Auditor | Acceso de solo lectura: creación denegada (RBAC) | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar catálogo exacto de valores de `indicacion_de_reposo` (texto libre vs. lista) con Coordinación.
- **Defectos abiertos:** `BUG-2608-04` (ítems de inicio y término de licencia repetidos — probable confusión entre las fechas de la licencia y las del reposo) y `BUG-2608-07` (el rótulo "ingreso ID" no se entiende).
- Posible integración futura con IMED para precargar datos de la LM electrónica (PRD §8.3) — fuera de alcance v1.

---

## [CEPA-071] Cálculo automático de días acumulados por paciente

**Épica:** EPIC-07 — Licencias Médicas
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.7.3
**Trazabilidad:** PRD §7.7.3 · §7.7.4 (CA textual) · Decisiones v4: D7

### Historia
Como **Administrativo del CEPA**, quiero **que el sistema calcule automáticamente los días acumulados de licencia por paciente** para **eliminar los cálculos manuales que generan errores**.

### Criterios de Aceptación (Gherkin)
- **CA-1** *(CA textual del PRD §7.7.4)*
  - **Dado** que un administrativo registra una nueva licencia médica para un paciente con **3 licencias previas**
  - **Cuando** guarda el registro
  - **Entonces** el sistema **calcula automáticamente el total de días acumulados sumando las 4 licencias** y lo muestra en la vista del paciente
- **CA-2**
  - **Dado** que se incluyen licencias extra-sistema registradas para el paciente (v4 D7)
  - **Cuando** se calcula el acumulado
  - **Entonces** estas también se suman al total, marcadas como origen extra-sistema
- **CA-3**
  - **Dado** que dos licencias del mismo paciente **se solapan en fechas**
  - **Cuando** se calcula el acumulado de días
  - **Entonces** el sistema aplica la regla de solapamiento definida (no doble-conteo de días calendario) y señala el solapamiento

### Reglas de Negocio
- **RN-1:** `dias_acumulados(paciente) = Σ cantidad_de_dias` de **todas** las LM vinculadas a su folio, incluidas las extra-sistema (v4 D7).
- **RN-2:** El recálculo se dispara automáticamente al crear, editar o anular cualquier LM del paciente (no requiere acción manual).
- **RN-3:** **Solapamiento:** si dos o más LM cubren días calendario comunes, el acumulado de **días calendario efectivos** no los cuenta dos veces; además se conserva el total bruto (suma simple) como dato auxiliar. Se marca visualmente el solapamiento para revisión administrativa.
- **RN-4:** Una LM **anulada/rechazada** (ej. por 77 BIS) se excluye del acumulado vigente pero se mantiene en el historial para trazabilidad.
- **RN-5:** El acumulado se muestra en la vista consolidada del paciente y alimenta el "Reporte de licencias médicas acumuladas" (PRD §7.9).
- **RN-6:** Borde de cálculo: paciente sin LM previas → acumulado = días de la primera LM registrada.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-071-01 | Positivo | Paciente con 3 LM previas: 10+15+7=32 días | Registrar 4ª LM de 8 días y guardar | LM4=8 días, sin solapamiento | Acumulado mostrado = 40 días (CA-1 §7.7.4) | Alta |
| TC-071-02 | Borde | Paciente sin LM previas | Registrar primera LM | LM1=12 días | Acumulado = 12 días (RN-6) | Media |
| TC-071-03 | Borde | Paciente con 2 LM solapadas | Registrar LM A=01–10/06 y LM B=06–15/06 | solapamiento 06–10/06 (5 días comunes) | Días calendario efectivos = 15 (no 20); total bruto=20 auxiliar; solapamiento señalado (RN-3) | Alta |
| TC-071-04 | Positivo | Paciente con 1 LM extra-sistema (20 días) + 1 LM en sistema (10 días) | Verificar acumulado | mix de orígenes | Acumulado = 30 días, LM extra-sistema marcada (CA-2 / RN-1) | Alta |
| TC-071-05 | Borde | Paciente con LM rechazada por 77 BIS | Anular/recalificar una LM y recalcular | LM anulada de 15 días | Acumulado vigente excluye los 15 días; LM permanece en historial (RN-4) | Media |
| TC-071-06 | Permisos | Usuario perfil Auditor | Visualizar acumulado del paciente | sesión Auditor | Lectura del acumulado permitida; sin posibilidad de editar LM que lo alteren | Media |

### Definición de Hecho (DoD)
- [ ] Cálculo implementado y desplegado en QA
- [ ] Todos los CA verificados (incl. CA textual §7.7.4)
- [ ] Tests unitarios + integración en verde (≥1 positivo y ≥1 de borde por la convención de cálculos)
- [ ] Endpoint de consulta de acumulado documentado en OpenAPI/Swagger
- [ ] Recálculo registrado en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar con Coordinación la regla de solapamiento preferida: ¿días calendario efectivos o suma bruta como total oficial? (afecta reportería §7.9).
- Definir si el acumulado se reinicia por año calendario, por episodio/siniestro, o es histórico total.

---

## [CEPA-072] Alerta de vencimiento de licencia

**Épica:** EPIC-07 — Licencias Médicas
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.7.3
**Trazabilidad:** PRD §7.7.3 · §7.7.4 (CA textual) · §7.11 · Decisiones v4: D1, D12 · Ref. EPIC-10 (Alertas y Tareas Automatizadas)

### Historia
Como **Administrativo del CEPA**, quiero **recibir una alerta cuando una licencia médica esté por vencer** para **no depender de mi memoria ni revisar la planilla cada día para detectar plazos críticos**.

### Criterios de Aceptación (Gherkin)
- **CA-1** *(CA textual del PRD §7.7.4, adaptado por v4 D1)*
  - **Dado** que una licencia médica **vence en los próximos 3 días hábiles**
  - **Cuando** el sistema ejecuta la revisión programada de alertas
  - **Entonces** se genera una **alerta visible para el administrativo asignado** (el médico tratante NO usa el sistema — v4 D1)
- **CA-2**
  - **Dado** que la alerta se generó
  - **Cuando** el administrativo asignado inicia sesión
  - **Entonces** la ve en su panel de notificaciones in-app filtrado por su rol y pacientes asignados (PRD §7.12)
- **CA-3**
  - **Dado** que la LM ya venció o fue anulada
  - **Cuando** corre la revisión de alertas
  - **Entonces** no se genera (ni se mantiene) alerta de "por vencer" para esa LM

### Reglas de Negocio
- **RN-1:** Umbral de alerta: la LM vence dentro de **3 días hábiles** (excluye sábados, domingos y festivos) contados desde la fecha de ejecución de la revisión. **El umbral es parametrizable por Coordinación** (v5 D21), no una constante del código; 3 días hábiles es el valor por defecto y está **pendiente de confirmación (PA-v5-04)**.
- **RN-1b (v5 D21 — regla completa):** la alerta declara **disparador** = LM próxima a vencer; **umbral** = parametrizable; **destinatario** = administrativo asignado; **canal** = in-app (P0) / correo (P1); **mensaje** = texto parametrizable dirigido al usuario administrativo; **cierre** = LM renovada, vencida o anulada.
- **RN-1c (v5 — reposo parcial):** las LM de **reposo parcial** se alertan de forma diferenciada de las de reposo total: el documento de la contraparte las menciona explícitamente junto a los días de vencimiento. La regla concreta es **PA-v5-04**; hasta definirla, el sistema marca visualmente el tipo de reposo en la alerta y **no** aplica un umbral distinto.
- **RN-2:** El destinatario es el **administrativo asignado** al caso/paciente. Por v4 D1 NO se notifica a clínicos.
- **RN-3:** Canal: **notificación in-app (P0)**. El correo electrónico es solo para alertas (v4 D12) y queda como **P1**.
- **RN-4:** La revisión se ejecuta como tarea programada (job diario) — alinear con EPIC-10. Idempotente: no duplica la alerta si ya existe una activa para la misma LM.
- **RN-5:** LM vencida, anulada o rechazada (77 BIS) no genera alerta de vencimiento próximo (RN se evalúa contra estado vigente).
- **RN-6:** Meta de negocio: **0% de vencimientos de licencia sin alerta previa** (OU4, PRD §3.1).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-072-01 | Positivo | LM vigente con término en 3 días hábiles; administrativo asignado | Ejecutar job de alertas | hoy=mié, término=lun siguiente (3 hábiles) | Alerta in-app generada para el administrativo asignado (CA-1) | Alta |
| TC-072-02 | Borde | LM cuyo término cae tras fin de semana | Ejecutar job en viernes | término=miércoles siguiente; sáb/dom no cuentan | Cálculo de 3 días hábiles correcto; alerta generada el día adecuado (RN-1) | Alta |
| TC-072-03 | Negativo | LM ya vencida o anentregada por 77 BIS | Ejecutar job de alertas | término=ayer / estado anulada | No se genera alerta de "por vencer" (CA-3 / RN-5) | Media |
| TC-072-04 | Borde | LM que ya tiene una alerta activa | Reejecutar job el mismo día | alerta previa vigente | No se duplica la alerta (idempotencia, RN-4) | Media |
| TC-072-05 | Permisos | Administrativo NO asignado al paciente | Revisar su panel de alertas | sesión de otro administrativo | No ve la alerta de esa LM (filtro por pacientes asignados, RN-2) | Alta |
| TC-072-07 | Positivo | Coordinación cambia el umbral en configuración | Cambiar de 3 a 5 días hábiles y ejecutar el job | umbral=5 | El job usa el valor nuevo sin redespliegue (RN-1, v5 D21) | Alta |
| TC-072-08 | Positivo | LM de reposo parcial próxima a vencer | Ejecutar job de alertas | tipo_reposo=parcial | La alerta identifica el reposo como parcial (RN-1c) | Media |
| TC-072-06 | Permisos | Usuario perfil Clínico (sin acceso al sistema) | n/a | v4 D1 | Confirmado: no existe destinatario clínico; alerta solo administrativa | Media |

### Definición de Hecho (DoD)
- [ ] Job de alertas implementado y desplegado en QA
- [ ] Todos los CA verificados (incl. CA textual §7.7.4)
- [ ] Tests unitarios + integración en verde (cálculo de días hábiles cubierto)
- [ ] Endpoint/consumo de alertas documentado en OpenAPI/Swagger (si aplica)
- [ ] Generación de alerta registrada en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar fuente del calendario de **festivos** chilenos para el cálculo de días hábiles.
- **Bloqueante (v5 PA-v5-04):** días de anticipación definitivos, tratamiento del **reposo parcial** y **texto del mensaje** para el usuario administrativo. La contraparte pidió explícitamente *"definir específicamente (regla)"*; el valor por defecto de 3 días hábiles **no está acordado**.
- El detalle del motor de alertas/notificaciones (panel in-app, dedupe, email P1) se especifica en **EPIC-10 — Alertas y Tareas Automatizadas**; esta historia define el disparador específico de LM.

---

## [CEPA-073] Trazabilidad de envío a ISL y licencias extra-sistema

**Épica:** EPIC-07 — Licencias Médicas
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.7.2
**Trazabilidad:** PRD §7.7.2 · §7.7.3 · Decisiones v4: D7

### Historia
Como **Administrativo del CEPA**, quiero **registrar el envío de cada LM al ISL, su EEAG/GAF y observaciones, y consultar el historial completo de licencias por paciente (incluidas las extra-sistema)** para **dar trazabilidad al ciclo de la licencia sin perder registros en el camino**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que una LM de origen laboral está registrada
  - **Cuando** el administrativo marca el envío a ISL con su estado y fecha
  - **Entonces** la LM refleja estado de envío (pendiente / enviado / rechazado) y la fecha, visibles en el historial del paciente
- **CA-2**
  - **Dado** que el administrativo registra el EEAG/GAF, la fecha de emisión y observaciones de la LM
  - **Cuando** guarda
  - **Entonces** estos datos quedan asociados a la LM y disponibles para auditoría
- **CA-3** *(v4 D7)*
  - **Dado** que existe una **licencia médica extra-sistema** del paciente
  - **Cuando** el administrativo la registra marcándola como extra-sistema
  - **Entonces** aparece en el **historial completo de licencias** del paciente y se incluye en sus días acumulados (ver CEPA-071)
- **CA-4**
  - **Dado** un auditor consultando un caso
  - **Cuando** abre el historial de LM del paciente
  - **Entonces** ve todas las licencias (en-sistema y extra-sistema) con su trazabilidad ISL, en modo solo lectura

### Reglas de Negocio
- **RN-1:** Campos de gestión §7.7.2: `envio_ISL` (estado + fecha), `EEAG_GAF` (**tramo del catálogo `gaf_tramo`**, v5 D18 — ya no un valor 1–100), `fecha_emision`, `observaciones`.
- **RN-2:** Estados de envío a ISL: {pendiente, enviado, rechazado}. `fecha_envio_ISL` obligatoria cuando estado = enviado o rechazado.
- **RN-3:** El **historial completo de licencias por paciente** (§7.7.3) lista todas las LM del folio ordenadas cronológicamente, con su origen (en-sistema / extra-sistema), estado de envío y diagnóstico.
- **RN-4:** Las **licencias extra-sistema** (v4 D7) se distinguen con una marca de origen y, al no tener envío ISL gestionado por CEPA, su estado ISL puede quedar como "no aplica / externo".
- **RN-5:** Un rechazo por **77 BIS** se refleja en el estado y observaciones, y dispara la exclusión del acumulado vigente (coordinado con CEPA-071 RN-4).
- **RN-6:** Solo perfiles con CRUD (Administrativo, Coordinación) editan la trazabilidad; **Auditor es solo lectura** (PRD §5.3).
- **RN-7:** Toda actualización de trazabilidad se registra en el log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-073-01 | Positivo | LM laboral registrada | Marcar envío a ISL = enviado con fecha y guardar | estado=enviado, fecha=02/06/2026 | Estado y fecha de envío visibles en historial (CA-1) | Alta |
| TC-073-02 | Negativo | LM con envío marcado | Guardar estado=enviado sin fecha | fecha vacía | Error de validación: fecha de envío obligatoria (RN-2) | Alta |
| TC-073-03 | Positivo | Paciente con LM extra-sistema | Registrar LM extra-sistema y abrir historial | origen=extra-sistema, 20 días | Aparece en historial marcada como extra-sistema y suma al acumulado (CA-3) | Alta |
| TC-073-04 | Borde | LM rechazada vía 77 BIS | Registrar rechazo ISL + observación | estado=rechazado, motivo 77 BIS | Estado/observación reflejados; excluida del acumulado vigente (RN-5) | Media |
| TC-073-05 | Borde | Catálogo de tramos de GAF cargado | Enviar un GAF que no corresponde a ningún tramo vía API | valor fuera del catálogo | Rechazo: solo se admiten tramos del catálogo (RN-1, v5 D18) | Media |
| TC-073-06 | Permisos | Usuario perfil Auditor | Intentar editar estado de envío ISL | sesión Auditor | Edición denegada; consulta del historial permitida (RN-6 / RBAC) | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD de trazabilidad + vista de historial implementados y desplegados en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) de historial y trazabilidad documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir si el envío a ISL será manual o, a futuro, integrado vía API/IMED (PRD §8.3) — integración fuera de alcance v1.
- Confirmar el conjunto mínimo de campos exigidos para una LM extra-sistema (puede faltar folio ISL u otros datos del flujo regular).
- **Bloqueante (v5 PA-v5-03):** listado definitivo de tramos de GAF. Los valores de GAF ya cargados como entero requieren migración con traza del valor original.

---

## [CEPA-074] Filtros del listado de licencias médicas

**Épica:** EPIC-07 — Licencias Médicas
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.7.3
**Trazabilidad:** Decisiones v5 (revisión ambiente de pruebas, sección *Licencias médicas*) · PRD §9 (rendimiento)

### Historia
Como **Administrativo del CEPA**, quiero **filtrar el listado de licencias médicas por médico, rango de fecha de emisión, rango de fecha de vencimiento, RUT y nombre del usuario** para **encontrar una licencia concreta en el módulo con mayor volumen de datos del sistema sin recorrer 1.584+ registros**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo abre el listado de licencias médicas
  - **Cuando** revisa los filtros disponibles
  - **Entonces** puede filtrar por **médico**, **rango de fecha de emisión**, **rango de fecha de vencimiento**, **RUT** y **nombre del usuario(a)**
- **CA-2**
  - **Dado** que el administrativo aplica varios filtros a la vez
  - **Cuando** ejecuta la búsqueda
  - **Entonces** el listado muestra únicamente las licencias que cumplen **todos** los filtros aplicados
- **CA-3**
  - **Dado** un filtro de rango de fechas
  - **Cuando** el administrativo indica solo la fecha inicial o solo la final
  - **Entonces** el rango se interpreta como abierto por el extremo no informado, sin obligar a completar ambos
- **CA-4**
  - **Dado** una combinación de filtros sin coincidencias
  - **Cuando** se ejecuta la búsqueda
  - **Entonces** el sistema informa "sin resultados" sin error y conservando los filtros aplicados
- **CA-5**
  - **Dado** el volumen real del módulo (1.584+ licencias)
  - **Cuando** se aplica cualquier combinación de filtros
  - **Entonces** el listado responde en **menos de 2 segundos** (RNF de rendimiento, PRD §9)

### Reglas de Negocio
- **RN-1:** Filtros disponibles: `médico`, `fecha_emision` (rango), `fecha_vencimiento` (rango), `RUT`, `nombre` (coincidencia parcial). Combinables con AND.
- **RN-2:** Los rangos de fecha admiten extremo abierto (solo desde, solo hasta).
- **RN-3:** El filtro por nombre es de coincidencia parcial e insensible a mayúsculas y acentos — un administrativo no escribe "Muñoz" con tilde correcta cada vez.
- **RN-4:** El listado es **paginado** e indexado por los campos filtrables; el filtrado ocurre en el servidor, nunca cargando el total de registros al navegador.
- **RN-5:** Los filtros aplicados se conservan al volver al listado desde el detalle de una licencia.
- **RN-6 (Permisos):** Todos los perfiles operativos consultan; Auditor en solo lectura.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-074-01 | Positivo | Listado con licencias de varios médicos | Filtrar por médico | Dr. X | Solo licencias de ese médico | Alta |
| TC-074-02 | Positivo | Licencias en distintas fechas | Filtrar por rango de emisión + RUT | 01/06–30/06, RUT 11.111.111-1 | Solo las licencias que cumplen ambos filtros (RN-1) | Alta |
| TC-074-03 | Borde | Filtro de rango de fechas | Informar solo "desde" | desde=01/06/2026 | Rango abierto hacia adelante; sin exigir "hasta" (RN-2) | Media |
| TC-074-04 | Borde | Paciente de apellido "Muñoz" | Buscar por nombre sin tilde y en minúsculas | "munoz" | Encuentra el registro (RN-3) | Alta |
| TC-074-05 | Negativo | — | Combinación de filtros sin coincidencias | médico X + junio 2019 | "Sin resultados", sin error, filtros conservados (CA-4) | Media |
| TC-074-06 | No funcional | Base con el volumen real (1.584+ LM) | Aplicar filtros combinados y medir | — | Respuesta < 2 s (CA-5, PRD §9) | Alta |
| TC-074-07 | Permisos | Sesión Auditor | Usar los filtros del listado | — | Consulta permitida; sin acceso a edición | Alta |

### Definición de Hecho (DoD)
- [ ] Filtros implementados y desplegados en QA
- [ ] Todos los CA verificados
- [ ] Filtrado y paginación **en el servidor**, con índices sobre los campos filtrables
- [ ] Rendimiento verificado **contra el volumen real de datos**, no contra un set de prueba pequeño
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint documentado en OpenAPI/Swagger
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar si "fecha de vencimiento" corresponde a `fecha_termino` de la LM o al fin del reposo — son campos distintos en `CEPA-070` (RN-1, RN-2) y la contraparte usó un único término. Relacionado con `BUG-2608-04`.
- Evaluar si los filtros deben poder guardarse como vista predefinida por usuario (no pedido; posible P2).

---

## [CEPA-075] Alerta por tramo de GAF en licencia médica

**Épica:** EPIC-07 — Licencias Médicas
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.7 · §7.11
**Trazabilidad:** Decisiones v5: D18, D21 · PA-v5-03, PA-v5-04 · Ref. `CEPA-100`

### Historia
Como **Administrativo del CEPA**, quiero **que el sistema alerte cuando una licencia médica se registra con un tramo de GAF que requiere atención** para **detectar los casos de mayor deterioro funcional sin revisar licencia por licencia**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que se registra o actualiza una LM con un tramo de GAF
  - **Cuando** ese tramo está dentro de los tramos configurados como "alertables"
  - **Entonces** el sistema genera una alerta in-app para el administrativo asignado
- **CA-2**
  - **Dado** que se registra una LM con un tramo de GAF fuera de los tramos alertables
  - **Cuando** corre la revisión de alertas
  - **Entonces** no se genera alerta
- **CA-3**
  - **Dado** que Coordinación modifica qué tramos son alertables
  - **Cuando** guarda la configuración
  - **Entonces** las alertas siguientes usan la configuración nueva, sin redespliegue
- **CA-4**
  - **Dado** que una LM ya generó una alerta de GAF activa
  - **Cuando** se reejecuta la revisión
  - **Entonces** la alerta no se duplica

### Reglas de Negocio
- **RN-1 (v5 D21 — regla completa):** **disparador** = registro o actualización de una LM con tramo de GAF; **umbral** = conjunto de tramos marcados como alertables en configuración; **destinatario** = administrativo asignado (y Coordinación, a confirmar); **canal** = in-app (P0) / correo (P1); **mensaje** = texto parametrizable; **cierre** = LM actualizada a un tramo no alertable, o alerta gestionada por el administrativo.
- **RN-2:** Los tramos alertables son **configurables por Coordinación**; no hay tramos alertables por defecto hasta que la contraparte los defina (**PA-v5-04**). Con la configuración vacía, la alerta simplemente no se dispara — nunca se inventa un criterio clínico.
- **RN-3:** Depende del catálogo de tramos de `CEPA-062` RN-3 (v5 D18); esta historia **no puede implementarse antes** de que exista ese catálogo (**PA-v5-03**).
- **RN-4:** Idempotencia sobre el motor de `CEPA-100`: una alerta activa por LM.
- **RN-5 (Permisos):** Auditor visualiza en solo lectura; no genera ni cierra alertas.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-075-01 | Positivo | Tramo `1-10%` configurado como alertable | Registrar LM con GAF=`1-10%` | tramo alertable | Alerta in-app generada para el administrativo asignado | Alta |
| TC-075-02 | Negativo | Tramo `81-90%` no alertable | Registrar LM con GAF=`81-90%` | tramo no alertable | No se genera alerta (CA-2) | Alta |
| TC-075-03 | Borde | Configuración de tramos alertables **vacía** | Registrar LM con cualquier tramo | sin configuración | No se genera ninguna alerta; el sistema no asume un criterio propio (RN-2) | Alta |
| TC-075-04 | Positivo | Coordinación agrega un tramo alertable | Cambiar configuración y registrar LM en ese tramo | configuración nueva | Alerta generada sin redespliegue (CA-3) | Alta |
| TC-075-05 | Borde | LM con alerta de GAF activa | Actualizar la LM sin cambiar el tramo | — | La alerta no se duplica (CA-4 / RN-4) | Media |
| TC-075-06 | Permisos | Sesión Auditor | Intentar cerrar la alerta | — | Acción denegada; visualización permitida | Alta |

### Definición de Hecho (DoD)
- [ ] Alerta implementada sobre el motor de `CEPA-100` y desplegada en QA
- [ ] Catálogo de tramos de GAF (v5 D18) implementado como precondición
- [ ] Todos los CA verificados
- [ ] **Regla escrita** (disparador, umbral, destinatario, canal, mensaje, cierre) documentada y visible en configuración
- [ ] Tests unitarios + integración en verde, incluida la idempotencia y el caso de configuración vacía
- [ ] Generación de alerta registrada en log de auditoría
- [ ] **Tramos alertables y texto del mensaje definidos por la contraparte** — es un criterio clínico-administrativo, no técnico
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- **Bloqueante (PA-v5-03):** sin el catálogo de tramos no hay nada sobre lo que alertar.
- **Bloqueante (PA-v5-04):** qué tramos ameritan alerta y qué debe decir el mensaje. **No corresponde que lo decidamos nosotros**: es un umbral clínico-administrativo del CEPA.
- Confirmar si Coordinación también recibe esta alerta o solo el administrativo asignado.

---

## Convenciones de Test Cases (recordatorio)
- **Tipo:** Positivo (happy path), Negativo (validación/error), Borde (límites/concurrencia/solapamiento), Permisos (RBAC), No funcional (rendimiento/seguridad).
- **ID:** `TC-07x-nn`.
- Todo cálculo automático (días acumulados) lleva al menos 1 TC positivo y 1 de borde.
- Toda historia con RBAC lleva al menos 1 TC de permisos. Perfiles válidos: **Coordinación, Administrativo, Auditor** (NO Clínico — v4 D1).
