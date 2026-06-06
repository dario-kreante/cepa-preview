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

### Glosario aplicable
| Término | Definición |
|---------|------------|
| **LM** | Licencia Médica. Tipos relevantes: **1** (enfermedad común), **5** (enfermedad/accidente del trabajo curativa), **6** (patología del embarazo / prórroga). |
| **ISL** | Instituto de Seguridad Laboral. Recibe el envío de las LM de casos de enfermedad/accidente laboral. |
| **GAF / EEAG** | Escala de Evaluación de la Actividad Global (Global Assessment of Functioning). Valor 1–100. |
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
- **RN-1:** Umbral de alerta: la LM vence dentro de **3 días hábiles** (excluye sábados, domingos y festivos) contados desde la fecha de ejecución de la revisión.
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
- **RN-1:** Campos de gestión §7.7.2: `envio_ISL` (estado + fecha), `EEAG_GAF` (1–100), `fecha_emision`, `observaciones`.
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
| TC-073-05 | Borde | EEAG/GAF fuera de rango | Ingresar EEAG=150 | valor >100 | Rechazo: GAF debe estar en 1–100 (RN-1) | Media |
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

---

## Convenciones de Test Cases (recordatorio)
- **Tipo:** Positivo (happy path), Negativo (validación/error), Borde (límites/concurrencia/solapamiento), Permisos (RBAC), No funcional (rendimiento/seguridad).
- **ID:** `TC-07x-nn`.
- Todo cálculo automático (días acumulados) lleva al menos 1 TC positivo y 1 de borde.
- Toda historia con RBAC lleva al menos 1 TC de permisos. Perfiles válidos: **Coordinación, Administrativo, Auditor** (NO Clínico — v4 D1).
