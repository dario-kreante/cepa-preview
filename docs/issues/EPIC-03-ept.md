# EPIC-03 — Seguimiento EPT (Estudio de Puesto de Trabajo)

**Módulo PRD:** 7.3
**Prioridad (MoSCoW):** P0 Must
**Reemplaza:** hoja Excel «Seguimiento EPT» (27 columnas)
**Perfiles operativos:** Coordinación · Administrativo · Auditor (NO Clínico — ver Decisiones v4 D1)

> **Importante (Decisiones v4 D1):** el proceso EPT lo gestiona un **funcionario administrativo**,
> no un EPTista clínico. El antiguo perfil Clínico no tiene acceso al Sistema CEPA; los clínicos
> trabajan directamente en las fichas SALUTEM/SAM. Por ello todas las historias de esta épica
> tienen como actor principal al perfil **Administrativo**, con lectura para Coordinación y Auditor.

El Módulo de Seguimiento EPT gestiona el proceso de Estudio de Puesto de Trabajo asociado a casos
de salud mental ocupacional: registro del caso y del empleador, gestión operativa del proceso
(evidencias, insumos, testigos, entrevistas) y control de los plazos regulatorios de informe EPT
y de entrega al ISL.

## Glosario de la épica
| Término | Definición |
|---------|------------|
| **EPT** | Estudio de Puesto de Trabajo. Evaluación de las condiciones laborales del puesto del trabajador, asociada a la calificación de una enfermedad/accidente de origen laboral. |
| **ISL** | Instituto de Seguridad Laboral. Organismo administrador al que el CEPA entrega los informes EPT dentro de plazos regulatorios. |
| **EISTA** | Profesional evaluador asignado que realiza el Estudio de Puesto de Trabajo (genera insumos y documentos de incumplimiento). En el sistema solo se **registra** como dato; el EISTA no es usuario operativo del Sistema CEPA. |
| **Factor de riesgo** | Condición del puesto/entorno laboral identificada como origen o agravante del caso (p. ej. carga, organización del trabajo, factores psicosociales). |

---

## [CEPA-030] Datos del caso EPT y del empleador

**Épica:** EPIC-03 — Seguimiento EPT (Estudio de Puesto de Trabajo)
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.3.1 · 7.3.2
**Trazabilidad:** PRD §7.3.1 · §7.3.2 · Decisiones v4: D1

### Historia
Como **administrativo**, quiero **registrar los datos del caso EPT (folio, fechas, trabajador, EISTA/evaluador, factor de riesgo) y del empleador (razón social, unidad/cargo/horario y correos de coordinación EPT), incluyendo si "Corresponde EPT"** para **iniciar el expediente del Estudio de Puesto de Trabajo con la información base correcta y sin transcribirla a una planilla Excel**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo está en el formulario de nuevo caso EPT
  - **Cuando** completa los campos obligatorios (folio, mes, fecha de ingreso, nombre, RUT y región del trabajador, EISTA/evaluador asignado, factor de riesgo) y guarda
  - **Entonces** el sistema crea el caso EPT, queda visible en el listado y búsquedas, y registra la operación en el log de auditoría.
- **CA-2**
  - **Dado** que un administrativo ingresa el RUT del trabajador
  - **Cuando** el RUT tiene dígito verificador inválido
  - **Entonces** el sistema muestra un mensaje de error específico y no permite guardar, conservando los demás datos ya ingresados.
- **CA-3**
  - **Dado** que un administrativo registra los datos del empleador
  - **Cuando** agrega los correos de coordinación EPT
  - **Entonces** el sistema permite hasta **2 contactos**, valida formato de correo y rechaza un tercer contacto.
- **CA-4**
  - **Dado** que un administrativo marca el campo "Corresponde EPT"
  - **Cuando** selecciona "No"
  - **Entonces** el caso queda registrado como "No corresponde EPT" y el sistema permite cerrarlo sin exigir los datos de gestión del proceso (CEPA-031/032).
- **CA-5**
  - **Dado** un usuario con perfil Auditor o Coordinación
  - **Cuando** abre un caso EPT
  - **Entonces** puede visualizar todos los datos en modo solo lectura, sin opciones de edición.

### Reglas de Negocio
- **RN-1:** Campos obligatorios del caso: folio, mes, fecha de ingreso, nombre, RUT y región del trabajador, EISTA/evaluador asignado, factor de riesgo y "Corresponde EPT" (Sí/No).
- **RN-2:** El RUT del trabajador debe validar dígito verificador (consistente con el módulo de Ingresos).
- **RN-3:** El folio se vincula al folio del paciente/caso del módulo de Ingresos; un caso EPT pertenece a un único folio.
- **RN-4:** El empleador acepta **máximo 2 correos** de coordinación EPT, cada uno con formato de correo válido.
- **RN-5:** "Corresponde EPT" = "No" exime de los datos obligatorios del proceso EPT (CEPA-031) y de plazos (CEPA-032); "Sí" los habilita como flujo siguiente.
- **RN-6 (RBAC):** Solo el perfil Administrativo crea/edita el caso EPT. Coordinación y Auditor tienen acceso de solo lectura. El perfil Clínico no existe en el sistema (D1).
- **RN-7:** Toda creación/edición de caso EPT se registra en el log de auditoría (quién, qué, cuándo).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-030-01 | Positivo | Administrativo autenticado, folio existente | Completar campos obligatorios del caso y empleador y guardar | Folio válido, RUT válido, factor de riesgo, EISTA, 2 correos | Caso EPT creado, visible en búsquedas, registrado en auditoría | Alta |
| TC-030-02 | Negativo | Administrativo en formulario | Ingresar RUT con DV inválido y guardar | RUT 12.345.678-0 (DV inválido) | Error específico de RUT, no guarda, conserva demás datos | Alta |
| TC-030-03 | Negativo | Administrativo en datos del empleador | Intentar agregar un 3.er correo de coordinación | 3 correos válidos | Sistema rechaza el 3.er contacto (máx 2) | Media |
| TC-030-04 | Borde | Administrativo en formulario | Marcar "Corresponde EPT" = No y guardar sin datos de proceso | Corresponde EPT = No | Caso guardado como "No corresponde", sin exigir gestión EPT | Media |
| TC-030-05 | Permisos | Usuario Auditor autenticado | Abrir caso EPT e intentar editar | Caso EPT existente | Vista solo lectura; acción de edición denegada | Alta |
| TC-030-06 | Negativo | Administrativo en formulario | Guardar sin factor de riesgo (obligatorio) | Campo factor de riesgo vacío | Validación bloquea guardado e indica campo obligatorio | Media |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar si el catálogo de "factor de riesgo" es lista cerrada parametrizable o texto libre.
- Confirmar relación 1:1 vs. 1:N entre folio del caso de Ingresos y caso EPT (un trabajador puede tener más de un EPT por siniestro — ver D2).

---

## [CEPA-031] Gestión del proceso EPT

**Épica:** EPIC-03 — Seguimiento EPT (Estudio de Puesto de Trabajo)
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.3.3
**Trazabilidad:** PRD §7.3.3 · Decisiones v4: D1

### Historia
Como **administrativo**, quiero **gestionar el proceso EPT (plazos de evidencia del denunciante e insumos de la empresa, testigos, insumos del EISTA / documentos de incumplimiento, número de entrevistas realizadas y observaciones)** para **llevar el seguimiento completo del estudio en una sola interfaz sin perder ninguno de los múltiples pasos del proceso**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un caso EPT con "Corresponde EPT" = Sí
  - **Cuando** el administrativo registra el plazo de evidencia del denunciante y el plazo de insumos de la empresa
  - **Entonces** el sistema guarda ambos plazos asociados al caso y los muestra en la vista del proceso.
- **CA-2**
  - **Dado** un caso EPT en gestión
  - **Cuando** el administrativo indica que hay testigos (Sí) y la cantidad
  - **Entonces** el sistema exige una cantidad mayor o igual a 1; si selecciona "No", deshabilita y deja en cero el campo cantidad.
- **CA-3**
  - **Dado** un caso EPT en gestión
  - **Cuando** el administrativo registra el número de entrevistas realizadas
  - **Entonces** el sistema acepta solo enteros mayores o iguales a cero y actualiza el avance del caso.
- **CA-4**
  - **Dado** un caso EPT en gestión
  - **Cuando** el administrativo adjunta/registra los insumos del EISTA o documentos de incumplimiento y agrega observaciones
  - **Entonces** el sistema guarda los registros vinculados al caso y deja traza en el log de auditoría.
- **CA-5**
  - **Dado** un caso EPT con "Corresponde EPT" = No
  - **Cuando** el administrativo intenta abrir la gestión del proceso
  - **Entonces** el sistema no exige los datos del proceso y muestra el caso como no aplicable a EPT.

### Reglas de Negocio
- **RN-1:** La gestión del proceso solo aplica a casos con "Corresponde EPT" = Sí (heredado de CEPA-030, RN-5).
- **RN-2:** Testigos es booleano (Sí/No); si "Sí", la cantidad debe ser entero ≥ 1; si "No", cantidad = 0 y campo deshabilitado.
- **RN-3:** Número de entrevistas realizadas es entero ≥ 0.
- **RN-4:** Los plazos (evidencia del denunciante, insumos de la empresa) son fechas; la fecha de plazo no puede ser anterior a la fecha de ingreso del caso.
- **RN-5:** Insumos del EISTA / documentos de incumplimiento se registran asociados al folio del caso EPT y quedan trazables.
- **RN-6 (RBAC):** Solo Administrativo edita la gestión del proceso; Coordinación y Auditor solo lectura.
- **RN-7:** Toda modificación de la gestión del proceso se registra en el log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-031-01 | Positivo | Caso EPT con Corresponde EPT = Sí | Registrar plazos, testigos=Sí (3), 2 entrevistas, insumos y observaciones; guardar | Plazos válidos, testigos 3, entrevistas 2 | Datos guardados y visibles; traza en auditoría | Alta |
| TC-031-02 | Negativo | Caso EPT en gestión | Indicar testigos=Sí y cantidad 0 | Testigos=Sí, cantidad=0 | Validación exige cantidad ≥ 1, no guarda | Alta |
| TC-031-03 | Negativo | Caso EPT en gestión | Ingresar número de entrevistas negativo | Entrevistas = -1 | Sistema rechaza valor, exige entero ≥ 0 | Media |
| TC-031-04 | Borde | Caso EPT con fecha de ingreso definida | Ingresar plazo de insumos anterior a fecha de ingreso | Plazo < fecha ingreso | Sistema rechaza fecha inconsistente | Media |
| TC-031-05 | Borde | Caso EPT en gestión | Cambiar testigos de Sí a No | Testigos=No | Cantidad se pone en 0 y se deshabilita | Baja |
| TC-031-06 | Permisos | Usuario Coordinación autenticado | Abrir gestión del proceso e intentar editar entrevistas | Caso EPT existente | Vista solo lectura; edición denegada | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar si "insumos del EISTA / documentos de incumplimiento" requieren adjunto de archivo o solo registro textual (relación con lectura de PDF, D12 — P1).
- Confirmar si el número de entrevistas alimenta algún indicador del dashboard.

---

## [CEPA-032] Plazos de informe EPT / portal ISL y alertas

**Épica:** EPIC-03 — Seguimiento EPT (Estudio de Puesto de Trabajo)
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.3.3 · 7.11
**Trazabilidad:** PRD §7.3.3 · §7.11 · Decisiones v4: D1 · Alertas → EPIC-10

### Historia
Como **administrativo**, quiero **gestionar los plazos de informe EPT y portal ISL, la fecha de entrega ISL y la fecha de envío/estado, con alertas automáticas de vencimiento** para **cumplir los plazos regulatorios del ISL sin depender de mi memoria ni de revisar la planilla cada día**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un caso EPT con "Corresponde EPT" = Sí
  - **Cuando** el administrativo registra el plazo de informe EPT, el plazo del portal ISL y la fecha de entrega ISL
  - **Entonces** el sistema guarda los plazos y calcula el estado de cumplimiento (en plazo / por vencer / vencido).
- **CA-2**
  - **Dado** un caso EPT con plazo de informe EPT o entrega ISL próximo a vencer
  - **Cuando** el sistema ejecuta su revisión programada de alertas
  - **Entonces** genera una alerta visible en el panel del administrativo asignado (in-app) según las reglas de EPIC-10.
- **CA-3**
  - **Dado** un caso EPT con informe ya enviado
  - **Cuando** el administrativo registra la fecha de envío y el estado (enviado)
  - **Entonces** el sistema marca el plazo como cumplido y deja de emitir alertas de vencimiento para ese hito.
- **CA-4**
  - **Dado** un caso EPT cuya fecha de entrega ISL ya pasó sin envío
  - **Cuando** el sistema evalúa los plazos
  - **Entonces** marca el caso como "vencido" y lo expone en el reporte/listado de cumplimiento de plazos.
- **CA-5**
  - **Dado** un usuario Coordinación o Auditor
  - **Cuando** consulta los plazos y estados del caso EPT
  - **Entonces** los visualiza en solo lectura, incluyendo el estado de cumplimiento, sin poder editarlos.

### Reglas de Negocio
- **RN-1:** Estado de cumplimiento de cada plazo: **en plazo** (fecha objetivo futura), **por vencer** (dentro de la ventana de alerta configurada), **vencido** (fecha objetivo pasada sin envío), **cumplido** (envío registrado en fecha).
- **RN-2:** La generación de alertas de plazo de informe EPT y entrega ISL se delega a la lógica común de **EPIC-10 (Alertas y Tareas Automatizadas)**; esta historia define los hitos y sus fechas objetivo.
- **RN-3:** La fecha de entrega ISL no puede ser anterior a la fecha de ingreso del caso ni al plazo de informe EPT.
- **RN-4:** Registrar la fecha de envío con estado "enviado" cierra el hito y detiene las alertas de vencimiento asociadas.
- **RN-5:** El cumplimiento de plazos ISL es un dato regulatorio: todo cambio de plazo, fecha de envío o estado queda en el log de auditoría.
- **RN-6 (RBAC):** Solo Administrativo edita plazos, fechas y estados; Coordinación y Auditor solo lectura.
- **RN-7:** Los casos con "Corresponde EPT" = No no generan plazos ni alertas EPT.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-032-01 | Positivo | Caso EPT Corresponde EPT = Sí | Registrar plazo informe EPT, plazo portal ISL y fecha entrega ISL; guardar | Fechas futuras coherentes | Plazos guardados, estado "en plazo" calculado | Alta |
| TC-032-02 | Positivo | Caso EPT con entrega ISL en ventana de alerta | Ejecutar revisión programada de alertas | Entrega ISL dentro de ventana configurada | Alerta in-app generada para el administrativo asignado (vía EPIC-10) | Alta |
| TC-032-03 | Borde | Caso EPT con entrega ISL = hoy sin envío | Ejecutar evaluación de plazos al inicio del día | Fecha entrega ISL = fecha actual, sin envío | Estado pasa a "por vencer/vencido" según regla; aparece en reporte de cumplimiento | Media |
| TC-032-04 | Negativo | Caso EPT en edición de plazos | Ingresar fecha entrega ISL anterior a fecha de ingreso | Entrega ISL < fecha ingreso | Sistema rechaza fecha inconsistente | Media |
| TC-032-05 | Positivo | Caso EPT con plazo por vencer | Registrar fecha de envío y estado "enviado" | Envío registrado | Hito marcado cumplido; cesan alertas de vencimiento | Alta |
| TC-032-06 | Permisos | Usuario Auditor autenticado | Abrir plazos del caso EPT e intentar editar fecha de envío | Caso EPT existente | Vista solo lectura; edición denegada | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Cálculo de estado de cumplimiento con TC positivo y de borde
- [ ] Operaciones registradas en log de auditoría
- [ ] Integración de alertas verificada con EPIC-10
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir la ventana de anticipación de la alerta de plazo EPT / entrega ISL (días hábiles) en conjunto con EPIC-10.
- Confirmar si "estado" de envío maneja valores adicionales (p. ej. rechazado/reenviado por el portal ISL) además de pendiente/enviado.
- Confirmar si el reporte de cumplimiento de plazos ISL es parte de EPIC-09 (Reportería) o de esta épica.
