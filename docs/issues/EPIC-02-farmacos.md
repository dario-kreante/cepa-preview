# EPIC-02 — Gestión de Fármacos

**Módulo PRD:** §7.2
**Prioridad (MoSCoW):** P0 Must
**Reemplaza:** hoja Excel «Gestión de Fármacos» (525+ registros, 21 columnas)
**Perfiles operativos:** Coordinación · Administrativo · Auditor (NO Clínico — ver Decisiones v4 D1)

Controla todo el ciclo de prescripción, dispensación y seguimiento farmacológico de cada paciente, vinculado al folio del módulo de Ingresos (EPIC-01). El registro farmacológico lo gestiona el equipo Administrativo; Coordinación y Auditor tienen lectura total (Auditor sin edición de datos clínicos).

## Historias
- **CEPA-020** — Registro farmacológico vinculado al folio (§7.2.1)
- **CEPA-021** — Historial clínico farmacológico y esquema (§7.2.2)
- **CEPA-022** — Gestión de recetas (§7.2.3, §7.2.5)
- **CEPA-023** — Seguimiento de tratamiento (§7.2.4)

---

## [CEPA-020] Registro farmacológico vinculado al folio

**Épica:** EPIC-02 — Gestión de Fármacos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.2.1
**Trazabilidad:** PRD §7.2.1 · Decisiones v4: D1

### Historia
Como **administrativo del CEPA**, quiero **crear el registro farmacológico de un paciente vinculándolo a su folio de Ingresos y capturar sus datos básicos, médico tratante y estado del caso** para **gestionar la prescripción y el seguimiento sin transcribir información a una planilla Excel**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo está en el formulario de nuevo registro farmacológico
  - **Cuando** selecciona un folio existente del módulo de Ingresos
  - **Entonces** el sistema pre-llena los datos básicos heredados del folio (mes, región de derivación, fecha de ingreso, nombre, RUT) y permite confirmarlos.
- **CA-2**
  - **Dado** que un administrativo completa el médico tratante asignado y el estado del caso farmacológico
  - **Cuando** guarda el registro
  - **Entonces** el registro farmacológico queda vinculado al folio y es visible desde el módulo de Ingresos.
- **CA-3**
  - **Dado** que un administrativo intenta crear un registro farmacológico sin folio asociado
  - **Cuando** hace clic en guardar
  - **Entonces** el sistema muestra un error específico de campo obligatorio sin perder los datos ya ingresados.

### Reglas de Negocio
- **RN-1:** El registro farmacológico debe vincularse a un folio existente del módulo de Ingresos (EPIC-01); no se permite registro huérfano.
- **RN-2:** Los datos básicos (mes, región de derivación, fecha de ingreso, nombre, RUT) se heredan del folio como fuente única de verdad; el administrativo los confirma pero no los re-digita.
- **RN-3:** Médico tratante asignado y estado del caso farmacológico son campos obligatorios.
- **RN-4:** Un folio puede tener a lo sumo un registro farmacológico activo; un reingreso con el mismo folio reutiliza/reactiva el registro asociado.
- **RN-5:** RBAC — solo Administrativo (y Coordinación) puede crear/editar; Auditor accede en solo lectura; el perfil Clínico no existe en el sistema (D1).
- **RN-6:** Toda operación CRUD queda registrada en el log de auditoría (quién, qué, cuándo).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-020-01 | Positivo | Folio existe en Ingresos | Seleccionar folio → confirmar datos básicos → asignar médico y estado → guardar | Folio 12345, médico Dr. X, estado "activo" | Registro creado, vinculado al folio y visible desde Ingresos | Alta |
| TC-020-02 | Negativo | En formulario sin folio | Completar médico y estado sin folio → guardar | Sin folio | Error de campo obligatorio; datos no se pierden | Alta |
| TC-020-03 | Negativo | Folio existe | Guardar sin médico tratante ni estado | Folio 12345 | Error específico de campos obligatorios | Alta |
| TC-020-04 | Borde | Folio ya tiene registro farmacológico activo | Intentar crear segundo registro para el mismo folio | Folio 12345 | Sistema reutiliza/reactiva el registro existente, no duplica | Media |
| TC-020-05 | Permisos | Sesión con perfil Auditor | Intentar crear/editar registro farmacológico | Usuario auditor | Acceso denegado a edición; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- El perfil Clínico no usa el sistema (D1): médico tratante es un dato de referencia, no un usuario con acceso.
- Estado del caso farmacológico: pendiente confirmar el catálogo de valores con Coordinación.

---

## [CEPA-021] Historial clínico farmacológico y esquema

**Épica:** EPIC-02 — Gestión de Fármacos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.2.2
**Trazabilidad:** PRD §7.2.2 · Decisiones v4: D7

### Historia
Como **administrativo del CEPA**, quiero **registrar los antecedentes previos de salud mental, el tratamiento farmacológico previo y la indicación actual (medicamento/dosis/frecuencia) como esquema farmacológico** para **mantener el historial clínico-farmacológico completo y trazable del paciente sin depender de planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo está en el registro farmacológico de un folio
  - **Cuando** ingresa antecedentes previos de salud mental y tratamiento farmacológico previo
  - **Entonces** el sistema guarda el historial estructurado vinculado al folio.
- **CA-2**
  - **Dado** que un administrativo registra una indicación farmacológica actual
  - **Cuando** especifica medicamento, dosis y frecuencia y guarda
  - **Entonces** el sistema crea una entrada del esquema farmacológico vigente del paciente.
- **CA-3**
  - **Dado** que un medicamento indicado no pertenece al catálogo del sistema
  - **Cuando** el administrativo lo marca como fármaco extra-sistema y guarda
  - **Entonces** el sistema acepta el registro y lo identifica como extra-sistema.

### Reglas de Negocio
- **RN-1:** Cada entrada de indicación actual del esquema requiere medicamento, dosis y frecuencia.
- **RN-2:** El esquema farmacológico es versionable: una nueva indicación no borra la anterior, se mantiene el historial completo por folio.
- **RN-3:** Debe contemplarse el registro de **fármacos extra-sistema** (no presentes en el catálogo institucional), marcados como tales (D7).
- **RN-4:** Antecedentes previos y tratamiento previo son campos de texto estructurado asociados al folio.
- **RN-5:** RBAC — Administrativo/Coordinación editan; Auditor solo lectura.
- **RN-6:** Operaciones CRUD registradas en log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-021-01 | Positivo | Registro farmacológico existe | Ingresar antecedentes + tratamiento previo + indicación actual → guardar | Sertralina 50 mg c/24h | Historial y esquema guardados y vinculados al folio | Alta |
| TC-021-02 | Negativo | En indicación actual | Guardar indicación sin dosis ni frecuencia | Solo "Sertralina" | Error de campos obligatorios del esquema | Alta |
| TC-021-03 | Positivo | Catálogo no contiene el fármaco | Marcar fármaco extra-sistema → completar dosis/frecuencia → guardar | Medicamento extranjero | Registro aceptado y etiquetado extra-sistema | Alta |
| TC-021-04 | Borde | Esquema con indicación previa vigente | Agregar nueva indicación | 2ª indicación | Historial conserva ambas; nueva queda como vigente | Media |
| TC-021-05 | Permisos | Perfil Auditor | Intentar editar el esquema | Usuario auditor | Acceso denegado a edición; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- **Estadísticas de fármacos por tratamiento, programa y profesional (D7)** se desarrollan en **EPIC-09 (Reportería y Dashboard)**, no en esta épica; aquí solo se garantiza la captura estructurada del esquema (incl. extra-sistema) que alimenta dichas estadísticas.
- Pendiente definir el origen del catálogo de medicamentos institucional vs. carga manual.

---

## [CEPA-022] Gestión de recetas

**Épica:** EPIC-02 — Gestión de Fármacos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.2.3
**Trazabilidad:** PRD §7.2.3 · §7.2.5 · Decisiones v4: D1, D12

### Historia
Como **administrativo del CEPA**, quiero **registrar y gestionar recetas con fechas de emisión, revisión y envío y la marca del medicamento, vinculadas al folio** para **controlar el ciclo completo de cada prescripción y recibir alertas de revisión próxima sin perder recetas en el camino**.

### Criterios de Aceptación (Gherkin)
- **CA-1** (textual PRD §7.2.5)
  - **Dado** que un administrativo registra una nueva receta para un paciente
  - **Cuando** guarda el registro
  - **Entonces** la receta aparece vinculada al folio del paciente y es visible desde el módulo de Ingresos.
- **CA-2** (textual PRD §7.2.5, alerta redirigida según D1)
  - **Dado** que una receta tiene fecha de revisión dentro de los próximos 5 días
  - **Cuando** el sistema ejecuta su proceso de alertas
  - **Entonces** se genera una alerta visible en el panel del administrativo asignado.

### Reglas de Negocio
- **RN-1:** Una receta se compone de fecha de emisión, fecha de revisión, fecha de envío de receta y marca del medicamento, y queda vinculada al folio.
- **RN-2:** Al guardar, la receta es visible desde el módulo de Ingresos (vista consolidada del folio).
- **RN-3:** El proceso programado de alertas genera una alerta cuando `fecha_revisión` está dentro de los próximos 5 días respecto de la fecha de ejecución.
- **RN-4:** **Redirección de alerta (D1):** el PRD §7.2.5 menciona alerta para "administrativo y médico tratante"; como el perfil Clínico no usa el sistema, la alerta se dirige **al administrativo asignado** (in-app; correo solo para alertas según D12). El médico tratante queda como dato informativo, sin notificación in-app.
- **RN-5:** Fecha de revisión no puede ser anterior a la fecha de emisión; fecha de envío no anterior a la emisión.
- **RN-6:** RBAC — Administrativo/Coordinación gestionan recetas; Auditor solo lectura.
- **RN-7:** Operaciones CRUD registradas en log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-022-01 | Positivo | Registro farmacológico existe | Crear receta con emisión, revisión, envío y marca → guardar | Emisión 01/06, revisión 20/06 | Receta vinculada al folio y visible desde Ingresos | Alta |
| TC-022-02 | Positivo | Receta con revisión 04/06; hoy 03/06 | Ejecutar proceso de alertas | revisión en 1 día | Alerta visible en panel del administrativo asignado | Alta |
| TC-022-03 | Borde | Receta con revisión exactamente a 5 días; hoy 03/06 | Ejecutar proceso de alertas | revisión 08/06 | Alerta generada (límite inclusivo de 5 días) | Media |
| TC-022-04 | Negativo | En formulario de receta | Ingresar revisión anterior a emisión → guardar | emisión 10/06, revisión 05/06 | Error de validación de fechas | Alta |
| TC-022-05 | Borde | Receta con revisión a 6 días | Ejecutar proceso de alertas | revisión 09/06 | No se genera alerta (fuera de ventana) | Media |
| TC-022-06 | Permisos | Perfil Auditor | Intentar crear/editar receta | Usuario auditor | Acceso denegado a edición; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Correo electrónico solo para alertas (D12); el canal in-app es el primario.
- La integración con IMED para receta electrónica está fuera de alcance v1 (diferible vía API, PA5).

---

## [CEPA-023] Seguimiento de tratamiento

**Épica:** EPIC-02 — Gestión de Fármacos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.2.4
**Trazabilidad:** PRD §7.2.4 · Decisiones v4: D7

### Historia
Como **administrativo del CEPA**, quiero **registrar la disminución de fármacos (Sí/No + plan), el cambio de esquema (Sí/No + detalle) y observaciones** para **dejar trazabilidad de la evolución farmacológica del paciente sin recurrir a planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo marca "disminución de fármacos = Sí"
  - **Cuando** guarda el registro
  - **Entonces** el sistema exige el detalle del plan de disminución antes de confirmar.
- **CA-2**
  - **Dado** que un administrativo marca "cambio de esquema = Sí"
  - **Cuando** guarda el registro
  - **Entonces** el sistema exige el detalle del nuevo esquema antes de confirmar.
- **CA-3**
  - **Dado** que un administrativo registra observaciones y banderas en "No"
  - **Cuando** guarda
  - **Entonces** el seguimiento queda vinculado al folio y visible desde Ingresos sin exigir detalles adicionales.

### Reglas de Negocio
- **RN-1:** Si "disminución de fármacos = Sí", el plan de disminución (texto) es obligatorio.
- **RN-2:** Si "cambio de esquema = Sí", el detalle del nuevo esquema es obligatorio y debería reflejarse en el esquema farmacológico (CEPA-021).
- **RN-3:** Observaciones es campo de texto libre opcional.
- **RN-4:** El seguimiento se vincula al folio y es visible desde el módulo de Ingresos.
- **RN-5:** RBAC — Administrativo/Coordinación editan; Auditor solo lectura.
- **RN-6:** Operaciones CRUD registradas en log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-023-01 | Positivo | Registro farmacológico existe | Disminución=Sí + plan, cambio=No, observaciones → guardar | Plan: bajar 25 mg/semana | Seguimiento guardado y vinculado al folio | Alta |
| TC-023-02 | Negativo | En seguimiento | Disminución=Sí sin plan → guardar | Sin texto de plan | Error: plan de disminución obligatorio | Alta |
| TC-023-03 | Negativo | En seguimiento | Cambio de esquema=Sí sin detalle → guardar | Sin detalle | Error: detalle de nuevo esquema obligatorio | Alta |
| TC-023-04 | Positivo | Registro farmacológico existe | Disminución=No, cambio=No, solo observaciones → guardar | Observación libre | Guardado sin exigir detalles | Media |
| TC-023-05 | Permisos | Perfil Auditor | Intentar editar el seguimiento | Usuario auditor | Acceso denegado a edición; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Cuando "cambio de esquema = Sí", evaluar la sincronización automática con la entrada vigente del esquema farmacológico (CEPA-021) para evitar doble digitación.
