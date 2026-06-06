# EPIC-01 — Ingresos y Gestión de Pacientes

**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1
**Reemplaza:** hoja Excel «Ingresos» (846+ registros, 27 columnas)
**Trazabilidad:** PRD §6.1, §7.1.1–§7.1.4 · Decisiones v4: D1, D2, D3, D4, D6, D9, D10, D11

Gestiona el ciclo de vida completo del paciente desde su ingreso hasta el alta: registro en formulario único, folio autogenerado con opción manual, búsqueda 360°, seguimiento del proceso clínico, cierre/alta, ODAS y validador de consentimiento. Perfiles operativos: Coordinación, Administrativo, Auditor (sin perfil Clínico, decisión v4 D1).

## Historias

| ID | Título | Perfil | Prioridad |
|----|--------|--------|-----------|
| CEPA-010 | Registrar nuevo ingreso en formulario único | Administrativo | P0 |
| CEPA-011 | Folio autogenerado con opción de ingreso manual | Administrativo | P0 |
| CEPA-012 | Búsqueda 360° del paciente | Administrativo | P0 |
| CEPA-013 | Seguimiento del proceso clínico del ingreso | Administrativo | P0 |
| CEPA-014 | Cierre y alta del caso | Administrativo | P0 |
| CEPA-015 | Registro de ODAS y alerta de vencimiento | Administrativo | P0 |
| CEPA-016 | Validador de consentimiento informado | Administrativo | P0 |

---

## [CEPA-010] Registrar nuevo ingreso en formulario único

**Épica:** EPIC-01 — Ingresos y Gestión de Pacientes
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1.1
**Trazabilidad:** PRD §6.1 · §7.1.1 · §7.1.4 · Decisiones v4: D4, D6

### Historia
Como **administrativo del CEPA**, quiero **registrar un nuevo ingreso con todos los datos del paciente en un formulario único** para **no tener que transcribir la información a una planilla Excel después de ingresarla en la ficha clínica**.

### Criterios de Aceptación (Gherkin)
- **CA-1** (PRD §7.1.4)
  - **Dado** que un administrativo está en el formulario de nuevo ingreso
  - **Cuando** ingresa un RUT válido que ya existe en el sistema
  - **Entonces** el sistema muestra los datos del paciente pre-llenados y permite confirmar o actualizar
- **CA-2** (PRD §7.1.4)
  - **Dado** que un administrativo completa todos los campos obligatorios
  - **Cuando** guarda el registro
  - **Entonces** el sistema genera un folio único automático y el registro aparece inmediatamente en las búsquedas
- **CA-3** (PRD §7.1.4)
  - **Dado** que un administrativo intenta guardar un ingreso con RUT inválido
  - **Cuando** hace clic en guardar
  - **Entonces** el sistema muestra un mensaje de error específico sin perder los datos ya ingresados
- **CA-4**
  - **Dado** que un administrativo está completando el formulario
  - **Cuando** intenta guardar sin completar campos obligatorios (sexo, edad, diagnóstico, tipo de derivación, etc.)
  - **Entonces** el sistema bloquea el guardado y resalta los campos faltantes
- **CA-5**
  - **Dado** que un administrativo despliega el campo "tipo de derivación"
  - **Cuando** revisa las opciones disponibles
  - **Entonces** solo aparecen valores válidos: DIEP, DIAT, PAPT a flujo AT, Reingreso FUMP, Reingreso SUSESO, Convenio U.Clínica, Proyecto, Particular, PAPT

### Reglas de Negocio
- **RN-1:** El RUT es obligatorio y debe validarse por dígito verificador (módulo 11); un RUT inválido impide guardar.
- **RN-2:** Campos obligatorios para datos limpios y comparables (v4 D6): nombre, RUT, sexo, edad, región, diagnóstico, tipo de derivación, modelo de tratamiento, tipo de ingreso. El sistema no persiste el registro si falta alguno.
- **RN-3:** Si el RUT ya existe, el sistema pre-llena los datos del paciente y exige confirmación o actualización antes de crear el nuevo ingreso (un mismo paciente puede tener varios ingresos).
- **RN-4:** Al guardar correctamente, el sistema genera un folio único (ver CEPA-011) y el registro queda visible de inmediato en búsquedas (RUT/nombre/folio).
- **RN-5:** Un error de validación (RUT inválido u otro) nunca descarta los datos ya ingresados en el formulario.
- **RN-6:** Tipos de derivación permitidos (v4 D4): DIEP, DIAT, PAPT a flujo AT, Reingreso FUMP, Reingreso SUSESO, Convenio U.Clínica, Proyecto, Particular, PAPT. El antiguo "convenio SOCORRO" ya no es válido.
- **RN-7:** Campos del formulario (§7.1.1): folio, mes y fecha de ingreso, fecha DIEP/DIAT, datos del paciente (nombre, RUT, región, teléfono, correo), tipo de derivación, razón social / centro de trabajo.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-010-01 | Positivo | Usuario administrativo autenticado | Completar todos los campos obligatorios y guardar | RUT 12.345.678-5 nuevo, derivación DIAT | Ingreso creado, folio único generado, visible en búsqueda | Alta |
| TC-010-02 | Positivo | RUT ya existente en el sistema | Ingresar RUT existente | RUT 11.111.111-1 (con ingreso previo) | Datos pre-llenados; permite confirmar/actualizar y crear nuevo ingreso | Alta |
| TC-010-03 | Negativo | Formulario con datos cargados | Ingresar RUT inválido y guardar | RUT 12.345.678-0 (DV erróneo) | Error específico de RUT; los datos cargados se conservan | Alta |
| TC-010-04 | Negativo | Formulario parcialmente lleno | Guardar omitiendo sexo y diagnóstico | Sexo y diagnóstico vacíos | Guardado bloqueado; campos faltantes resaltados | Alta |
| TC-010-05 | Borde | Formulario abierto | Seleccionar tipo de derivación inexistente vía API | derivación = "SOCORRO" | Rechazo de valor no permitido (lista cerrada v4 D4) | Media |
| TC-010-06 | Permisos | Usuario perfil Auditor autenticado | Intentar abrir/guardar formulario de nuevo ingreso | — | Acceso denegado (Auditor es solo lectura) | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar catálogo de regiones/comunas y de diagnósticos a usar (alineación con dashboard, v4 D5).
- Migración de los 846+ registros históricos puede arrastrar RUT/folios no estándar (ver PA7).

---

## [CEPA-011] Folio autogenerado con opción de ingreso manual

**Épica:** EPIC-01 — Ingresos y Gestión de Pacientes
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1.1
**Trazabilidad:** PRD §7.1.1 · Decisiones v4: D2

### Historia
Como **administrativo del CEPA**, quiero **que el folio se genere automáticamente pero pueda ingresarlo manualmente cuando corresponda** para **mantener el folio anterior en reingresos, respetar folios pre-asignados del Excel y cargar ingresos con la fecha del día hábil correcto**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo crea un ingreso nuevo sin indicar folio
  - **Cuando** guarda el registro
  - **Entonces** el sistema asigna un folio secuencial automático único
- **CA-2**
  - **Dado** que un paciente reingresa tras el alta
  - **Cuando** el administrativo elige la opción de folio manual e ingresa el folio anterior
  - **Entonces** el sistema acepta el folio manual y vincula el reingreso a ese folio
- **CA-3**
  - **Dado** que un administrativo carga un ingreso recibido después de las 15:00 de lunes a jueves
  - **Cuando** registra el ingreso
  - **Entonces** el sistema permite asignar la fecha del día hábil siguiente
- **CA-4**
  - **Dado** un mismo RUT con una DIAT (2020) y una DIEP (2026)
  - **Cuando** se registra el segundo caso
  - **Entonces** el sistema diferencia reingreso de nueva denuncia por número de siniestro

### Reglas de Negocio
- **RN-1:** El folio por defecto es secuencial automático, único y no reutilizable entre ingresos distintos.
- **RN-2:** Existe opción de ingreso manual de folio para tres casos (v4 D2): reingresos que mantienen el folio anterior, folios pre-asignados desde el Excel histórico, e ingresos posteriores a las 15:00 (lun–jue) cargados con fecha del día hábil siguiente.
- **RN-3:** Un folio manual no puede colisionar con un folio secuencial ya emitido salvo que sea un reingreso explícito del mismo paciente.
- **RN-4:** Reingreso vs. nueva denuncia bajo el mismo RUT se diferencia por número de siniestro; un nuevo número de siniestro indica nueva denuncia.
- **RN-5:** El contador secuencial automático debe continuar sin saltos no controlados tras un ingreso manual.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-011-01 | Positivo | Administrativo autenticado | Crear ingreso sin folio | — | Folio secuencial automático único asignado | Alta |
| TC-011-02 | Positivo | Paciente con folio previo F-001 dado de alta | Reingreso con folio manual F-001 | Folio F-001, nuevo siniestro | Reingreso vinculado a F-001 aceptado | Alta |
| TC-011-03 | Positivo | Ingreso recibido a las 16:00 día martes | Registrar con fecha día hábil siguiente | Fecha = miércoles | Ingreso cargado con fecha del día hábil siguiente | Media |
| TC-011-04 | Negativo | Folio F-100 ya emitido para otro paciente | Ingresar manualmente F-100 para paciente distinto sin reingreso | Folio F-100 | Rechazo por colisión de folio | Alta |
| TC-011-05 | Borde | Mismo RUT con DIAT 2020 | Registrar DIEP 2026 con siniestro distinto | 2 siniestros distintos | Sistema lo trata como nueva denuncia diferenciada por siniestro | Media |
| TC-011-06 | Permisos | Usuario perfil Auditor | Intentar editar folio manualmente | — | Acceso denegado | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Pendiente confirmar con Coordinación si los reingresos generan nuevo folio o se diferencian solo por número de siniestro (v4 D2).
- Definir formato del folio (prefijo/año/secuencial) compatible con folios históricos del Excel.

---

## [CEPA-012] Búsqueda 360° del paciente

**Épica:** EPIC-01 — Ingresos y Gestión de Pacientes
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1 (transversal)
**Trazabilidad:** PRD §6.1 · OU3 · API §8.2 (Pacientes)

### Historia
Como **administrativo del CEPA**, quiero **buscar un paciente por RUT, nombre o folio y ver todas sus dimensiones (ingresos, fármacos, licencias, controles, reintegro) en una sola pantalla** para **responder rápidamente consultas del equipo clínico o del propio paciente sin abrir múltiples planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo está en la pantalla de búsqueda
  - **Cuando** ingresa un RUT, nombre o folio existente
  - **Entonces** el sistema muestra el paciente con todas sus dimensiones (ingresos, fármacos, licencias, controles, reintegro) en una sola pantalla
- **CA-2**
  - **Dado** que un administrativo solicita el estado completo de un caso
  - **Cuando** ejecuta la búsqueda
  - **Entonces** el sistema presenta el estado consolidado en menos de 10 segundos (OU3)
- **CA-3**
  - **Dado** que el término buscado no corresponde a ningún paciente
  - **Cuando** se ejecuta la búsqueda
  - **Entonces** el sistema informa que no hay resultados sin error
- **CA-4**
  - **Dado** un nombre parcial o con coincidencias múltiples
  - **Cuando** se busca
  - **Entonces** el sistema lista los pacientes coincidentes para seleccionar

### Reglas de Negocio
- **RN-1:** La búsqueda admite tres criterios: RUT, nombre (parcial) y folio.
- **RN-2:** El estado completo del caso (todas sus dimensiones) debe obtenerse en < 10 segundos (objetivo OU3), con respuesta del sistema < 2 s para volúmenes actuales.
- **RN-3:** La vista consolida datos de los módulos Ingresos, Fármacos, Licencias, Controles y Reintegro vinculados por folio/RUT.
- **RN-4:** El acceso a la vista 360° respeta RBAC; el perfil Auditor accede en solo lectura.
- **RN-5:** Búsqueda sin coincidencias retorna estado vacío controlado, nunca un error de sistema.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-012-01 | Positivo | Paciente con datos en varios módulos | Buscar por RUT | RUT 11.111.111-1 | Vista 360° con ingresos, fármacos, licencias, controles, reintegro | Alta |
| TC-012-02 | Positivo | Paciente existente | Buscar por folio | Folio F-001 | Paciente correcto mostrado | Alta |
| TC-012-03 | No funcional | Paciente con historial extenso | Medir tiempo de carga del estado completo | — | Estado completo en < 10 s (OU3) | Alta |
| TC-012-04 | Negativo | — | Buscar RUT inexistente | RUT 99.999.999-9 | Mensaje "sin resultados" sin error | Media |
| TC-012-05 | Borde | Varios pacientes con apellido común | Buscar por nombre parcial | "González" | Lista de coincidencias para seleccionar | Media |
| TC-012-06 | Permisos | Usuario perfil Auditor | Abrir vista 360° | — | Acceso de solo lectura (sin edición) | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Requiere paginación e indexación desde el diseño (mitigación de rendimiento, PRD §12.4).
- Confirmar qué dimensiones se cargan en la vista inicial vs. bajo demanda para cumplir el objetivo de < 10 s.

---

## [CEPA-013] Seguimiento del proceso clínico del ingreso

**Épica:** EPIC-01 — Ingresos y Gestión de Pacientes
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1.2
**Trazabilidad:** PRD §7.1.2 · Decisiones v4: D10

### Historia
Como **administrativo del CEPA**, quiero **registrar y rastrear el avance del ingreso por las etapas del proceso clínico** para **conocer en todo momento el estado de cada caso sin cruzar planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un ingreso registrado
  - **Cuando** el administrativo registra primera acogida y estado del consentimiento informado
  - **Entonces** el sistema guarda fecha de acogida y estado de consentimiento en el caso
- **CA-2**
  - **Dado** un ingreso en evaluación
  - **Cuando** se registra la evaluación médica (estado realizada/pendiente/no aplica, médico asignado, diagnóstico) y la evaluación psicológica (estado, psicólogo asignado)
  - **Entonces** el sistema actualiza el avance del proceso del caso
- **CA-3**
  - **Dado** un ingreso con plazo de informe definido por programa
  - **Cuando** la evaluación no se realiza dentro del plazo establecido por programa
  - **Entonces** el validador de estado indica incumplimiento de plazo (v4 D10)
- **CA-4**
  - **Dado** un ingreso en proceso
  - **Cuando** se registra obstaculización, plazo y fecha de envío de informe, y RECA EP/EC
  - **Entonces** el sistema almacena dichos hitos y los muestra en el seguimiento

### Reglas de Negocio
- **RN-1:** Hitos rastreados (§7.1.2): fecha de primera acogida y estado de consentimiento; evaluación médica (estado, médico, diagnóstico); evaluación psicológica (estado, psicólogo); obstaculización (sí/no); plazo y fecha real de envío de informe; RECA EP/EC.
- **RN-2:** Estados de evaluación válidos: realizada / pendiente / no aplica.
- **RN-3:** Validador de plazos por programa (v4 D10): el sistema calcula si la evaluación se realizó dentro del plazo del programa correspondiente y expone un estado de cumplimiento.
- **RN-4:** El registro de cada hito queda con trazabilidad (quién y cuándo) en el log de auditoría.
- **RN-5:** El perfil Auditor visualiza el seguimiento en solo lectura.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-013-01 | Positivo | Ingreso creado | Registrar primera acogida y consentimiento | Fecha acogida, consentimiento firmado | Hitos guardados y visibles en seguimiento | Alta |
| TC-013-02 | Positivo | Ingreso en evaluación | Registrar eval. médica y psicológica con estados | Médico, psicólogo, diagnóstico | Avance del proceso actualizado | Alta |
| TC-013-03 | Positivo | Programa con plazo definido | Registrar evaluación dentro de plazo | Fecha dentro de plazo | Validador marca "en plazo" | Alta |
| TC-013-04 | Negativo | Programa con plazo definido | Evaluación fuera de plazo | Fecha vencida | Validador marca "fuera de plazo" | Alta |
| TC-013-05 | Borde | Evaluación marcada "no aplica" | Guardar caso sin médico asignado | estado = no aplica | Aceptado sin exigir médico/diagnóstico | Media |
| TC-013-06 | Permisos | Usuario perfil Auditor | Intentar editar un hito del seguimiento | — | Acceso denegado a edición | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir tabla de plazos por programa para el validador (v4 D10).
- Médico/psicólogo se registran como dato administrativo (el perfil Clínico no opera el sistema, v4 D1).

---

## [CEPA-014] Cierre y alta del caso

**Épica:** EPIC-01 — Ingresos y Gestión de Pacientes
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1.3
**Trazabilidad:** PRD §7.1.3 · Decisiones v4: D6, D11

### Historia
Como **administrativo del CEPA**, quiero **registrar el cierre y alta del caso con su estado, tipo de alta y observaciones** para **dejar trazado el término del proceso del paciente de forma consistente**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un caso activo
  - **Cuando** el administrativo cambia el estado a cerrado o derivado
  - **Entonces** el sistema actualiza el estado del caso y lo refleja en la vista del paciente
- **CA-2**
  - **Dado** un cierre de caso
  - **Cuando** el administrativo registra el tipo de alta (terapéutica, médica, psicológica, abandono o derivación)
  - **Entonces** el sistema guarda el tipo de alta y la fecha asociada
- **CA-3**
  - **Dado** un caso que requiere seguimiento especial
  - **Cuando** el administrativo activa el flag de revisión y agrega observaciones generales
  - **Entonces** el sistema persiste el flag y el texto libre de observaciones
- **CA-4**
  - **Dado** que la organización opta por una sola fecha de alta (v4 D11)
  - **Cuando** se cierra el caso
  - **Entonces** el sistema registra la fecha de la última atención como fecha de alta única

### Reglas de Negocio
- **RN-1:** Estados de caso válidos (§7.1.3): activo, cerrado, derivado.
- **RN-2:** Tipos de alta válidos (§7.1.3, v4 D6): alta terapéutica, alta médica, alta psicológica, abandono, derivación.
- **RN-3:** El flag de revisión de caso marca seguimiento especial; las observaciones son texto libre.
- **RN-4:** Evaluar una única fecha de alta (última atención) independiente del tipo, para simplificar (v4 D11, decisión pendiente de confirmar con Coordinación).
- **RN-5:** Todo cambio de estado/alta queda registrado en el log de auditoría con autor y fecha.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-014-01 | Positivo | Caso activo | Cambiar estado a cerrado con alta terapéutica | tipo alta = terapéutica | Estado y tipo de alta guardados y visibles | Alta |
| TC-014-02 | Positivo | Caso activo | Derivar caso con observaciones | estado = derivado | Estado derivado + observaciones persistidas | Alta |
| TC-014-03 | Positivo | Caso a cerrar | Registrar fecha de alta = última atención | fecha última atención | Fecha de alta única registrada (v4 D11) | Media |
| TC-014-04 | Negativo | Caso a cerrar | Guardar alta con tipo no permitido | tipo = "otro" | Rechazo por valor fuera de catálogo | Alta |
| TC-014-05 | Borde | Caso con flag de revisión | Cerrar con flag de revisión activo | revisión = sí | Caso cerrado conservando flag de revisión | Media |
| TC-014-06 | Permisos | Usuario perfil Auditor | Intentar cerrar/dar de alta un caso | — | Acceso denegado | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar con Coordinación la decisión de fecha de alta única vs. múltiples fechas por tipo (v4 D11).

---

## [CEPA-015] Registro de ODAS y alerta de vencimiento

**Épica:** EPIC-01 — Ingresos y Gestión de Pacientes
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1 (requisito nuevo)
**Trazabilidad:** Decisiones v4: D3 · PRD §7.11 (alertas)

### Historia
Como **administrativo del CEPA**, quiero **registrar las ODAS (órdenes de primera atención) con su fecha de vencimiento y recibir alerta de las que están por vencer** para **gestionar las atenciones dentro de la vigencia del documento sin depender de revisión manual**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un paciente/ingreso
  - **Cuando** el administrativo registra una ODA actualizada con su fecha de vencimiento
  - **Entonces** el sistema guarda la ODA vinculada al folio del paciente
- **CA-2**
  - **Dado** una ODA con fecha de vencimiento próxima
  - **Cuando** el sistema ejecuta su proceso de alertas
  - **Entonces** se genera una alerta visible de "ODA por vencer" en el panel del administrativo
- **CA-3**
  - **Dado** una ODA existente
  - **Cuando** el administrativo registra una ODA actualizada
  - **Entonces** el sistema conserva el historial y refleja la ODA vigente

### Reglas de Negocio
- **RN-1:** Una ODA es la orden de primera atención, documento administrativo con plazo de vigencia/vencimiento; se ingresa manualmente porque no está en la ficha clínica (v4 D3).
- **RN-2:** Cada ODA registra al menos: documento/identificador de ODA y fecha de vencimiento, vinculada al folio del paciente.
- **RN-3:** El sistema genera alerta in-app de ODAS por vencer dentro de la ventana definida; el correo puede usarse solo para alertas (v4 D12).
- **RN-4:** El reporte de ODAS vencidas queda fuera de esta historia (corresponde a EPIC-09).
- **RN-5:** Registrar una ODA actualizada no elimina las anteriores; se conserva trazabilidad.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-015-01 | Positivo | Ingreso existente | Registrar ODA con fecha de vencimiento | Vence en 20 días | ODA guardada y vinculada al folio | Alta |
| TC-015-02 | Positivo | ODA próxima a vencer | Ejecutar proceso de alertas | Vence en 3 días | Alerta "ODA por vencer" visible para el administrativo | Alta |
| TC-015-03 | Borde | ODA que vence hoy | Ejecutar proceso de alertas | Vence = fecha actual | Alerta generada en el límite de vigencia | Media |
| TC-015-04 | Negativo | Registro de ODA | Guardar ODA sin fecha de vencimiento | fecha vacía | Rechazo por campo obligatorio | Alta |
| TC-015-05 | Positivo | ODA vigente registrada | Registrar ODA actualizada | nueva ODA | ODA vigente actualizada; historial conservado | Media |
| TC-015-06 | Permisos | Usuario perfil Auditor | Intentar registrar/editar ODA | — | Acceso denegado | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir la ventana de anticipación de la alerta de ODAS por vencer (p. ej. 5 días).
- El reporte de ODAS vencidas se especifica en EPIC-09.

---

## [CEPA-016] Validador de consentimiento informado

**Épica:** EPIC-01 — Ingresos y Gestión de Pacientes
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.1.2
**Trazabilidad:** PRD §7.1.2 · §7.11 · Decisiones v4: D9

### Historia
Como **administrativo del CEPA**, quiero **un validador que controle el estado del consentimiento informado firmado** para **garantizar que ningún tratamiento se inicie sin consentimiento válido**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un ingreso sin consentimiento informado firmado
  - **Cuando** se intenta iniciar el tratamiento
  - **Entonces** el sistema bloquea el inicio e indica que el consentimiento es obligatorio
- **CA-2**
  - **Dado** un ingreso con consentimiento firmado registrado
  - **Cuando** se inicia el tratamiento
  - **Entonces** el validador marca el consentimiento como cumplido y permite continuar
- **CA-3**
  - **Dado** un ingreso con consentimiento pendiente
  - **Cuando** el sistema ejecuta sus alertas de protocolo
  - **Entonces** se genera una alerta de "consentimiento informado pendiente"
- **CA-4**
  - **Dado** el formulario de consentimiento
  - **Cuando** el administrativo registra el estado del consentimiento
  - **Entonces** el sistema permite indicar/adjuntar la evidencia según el mecanismo definido

### Reglas de Negocio
- **RN-1:** El consentimiento informado firmado es obligatorio para iniciar tratamiento (v4 D9); sin él, el sistema impide el inicio.
- **RN-2:** El validador expone el estado del consentimiento: firmado / pendiente.
- **RN-3:** Un consentimiento pendiente genera alerta de cumplimiento de protocolo (PRD §7.11).
- **RN-4:** El mecanismo de adjunto/origen del consentimiento está por definir (nota abierta v4 D9): puede ser carga de archivo o referencia desde la ficha clínica.
- **RN-5:** El estado del consentimiento y su evidencia quedan en el log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-016-01 | Negativo | Ingreso sin consentimiento firmado | Intentar iniciar tratamiento | consentimiento = pendiente | Inicio bloqueado; mensaje de obligatoriedad | Alta |
| TC-016-02 | Positivo | Ingreso con consentimiento firmado | Iniciar tratamiento | consentimiento = firmado | Validador "cumplido"; tratamiento habilitado | Alta |
| TC-016-03 | Positivo | Ingreso con consentimiento pendiente | Ejecutar alertas de protocolo | — | Alerta "consentimiento pendiente" generada | Alta |
| TC-016-04 | Borde | Consentimiento marcado firmado sin evidencia adjunta | Guardar estado | sin archivo | Comportamiento según mecanismo definido (validar nota D9) | Media |
| TC-016-05 | Permisos | Usuario perfil Auditor | Intentar cambiar estado de consentimiento | — | Acceso denegado (solo lectura) | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- **Abierta (v4 D9):** definir cómo se adjunta / de dónde proviene el consentimiento (carga de archivo vs. referencia a ficha clínica SALUTEM/SAM). El aplicativo no escribe sobre SALUTEM (v4 D12).
