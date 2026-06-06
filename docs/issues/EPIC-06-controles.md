# EPIC-06 — Controles Médicos

**Módulo PRD:** 7.6
**Prioridad (MoSCoW):** P0 Must
**Reemplaza:** hoja «Controles Médicos» (24 columnas)
**Perfiles operativos:** Coordinación · Administrativo · Auditor (NO Clínico — ver Decisiones v4 · D1)

> Gestiona la programación y el seguimiento de los controles médicos periódicos:
> registro del control, cálculo automático de la semana, programación del próximo
> control con estado de agenda en SALUTEM/SAM, y licencias/RECA asociadas.

## Glosario de la épica
- **GAF / EEAG:** Escala de Evaluación de la Actividad Global (Global Assessment of Functioning). Puntaje 0–100 del funcionamiento global del paciente.
- **RECA:** Resolución de Calificación (documento de la mutualidad/ISL).
- **LM:** Licencia Médica.
- **Reposo total:** la persona no puede trabajar durante el período de la licencia.
- **Reposo parcial:** la persona puede trabajar parcialmente (media jornada u horario reducido) durante la licencia.

## Historias
- **CEPA-060** — Registro de control y cálculo automático de semana
- **CEPA-061** — Programación del próximo control y estado de agenda
- **CEPA-062** — Licencias y RECA asociadas al control

---

## [CEPA-060] Registro de control y cálculo automático de semana

**Épica:** EPIC-06 — Controles Médicos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.6
**Trazabilidad:** PRD §7.6.1 · §7.6.2 (semana del control) · Decisiones v4: D1

### Historia
Como **Administrativo**, quiero **registrar un control médico con los datos del control y del paciente, y que el sistema calcule automáticamente la semana del control** para **eliminar el cálculo manual de semanas que genera errores y mantener consistente el seguimiento periódico**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un administrativo está en el formulario de nuevo control médico
  - **Cuando** ingresa folio, región de derivación, fecha de ingreso, paciente (nombre, RUT) y médico tratante, y guarda
  - **Entonces** el sistema persiste el control vinculado al folio del paciente y lo muestra en la vista de gestión de controles médicos.
- **CA-2**
  - **Dado** que el control tiene fecha de ingreso del paciente y fecha del control
  - **Cuando** se guarda el registro
  - **Entonces** el sistema calcula automáticamente la **semana del control** = nº de semana transcurrida desde la fecha de ingreso hasta la fecha del control, y la muestra en modo solo lectura.
- **CA-3**
  - **Dado** que un administrativo ingresa un RUT con dígito verificador inválido
  - **Cuando** hace clic en guardar
  - **Entonces** el sistema muestra un mensaje de error específico sin perder los datos ya ingresados.
- **CA-4**
  - **Dado** que el folio ingresado no corresponde a ningún paciente con ingreso registrado
  - **Cuando** intenta guardar el control
  - **Entonces** el sistema bloquea el guardado e informa que el control debe asociarse a un folio existente.

### Reglas de Negocio
- **RN-1:** El control médico **debe** asociarse a un folio de paciente ya existente en el módulo de Ingresos (§7.1). No se crean pacientes desde este módulo.
- **RN-2:** RUT obligatorio y validado con dígito verificador.
- **RN-3 (CÁLCULO AUTOMÁTICO):** `semana_control = floor((fecha_control − fecha_ingreso) / 7) + 1`. La semana 1 cubre los días 0–6 desde la fecha de ingreso. El campo es de solo lectura (no editable manualmente).
- **RN-4 (Borde):** Si `fecha_control = fecha_ingreso`, la semana del control es **1**. Si `fecha_control < fecha_ingreso`, el sistema rechaza el registro (la fecha del control no puede ser anterior al ingreso).
- **RN-5:** Campos obligatorios: folio, región de derivación, fecha de ingreso, nombre, RUT, médico tratante (calidad de datos — Decisiones v4 · D6).
- **RN-6 (Permisos):** Coordinación y Administrativo pueden crear/editar; Auditor solo lectura.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-060-01 | Positivo | Folio 1024 existe; admin autenticado | Completar todos los campos y guardar | fecha_ingreso=2026-01-05, fecha_control=2026-02-02 | Control guardado; semana_control = **5** | Alta |
| TC-060-02 | Positivo (cálculo, TC positivo) | Folio existe | Guardar control en día intermedio de la semana | fecha_ingreso=2026-03-02, fecha_control=2026-03-10 | semana_control = **2** | Alta |
| TC-060-03 | Negativo | Admin en formulario | Ingresar RUT inválido y guardar | RUT=12.345.678-0 (DV erróneo) | Error de DV; datos conservados; no persiste | Alta |
| TC-060-04 | Negativo | Folio inexistente | Guardar control con folio no registrado | folio=99999 | Bloqueo: "folio inexistente"; no persiste | Alta |
| TC-060-05 | Borde (cálculo, TC borde) | Folio existe | Guardar control el mismo día del ingreso | fecha_ingreso=fecha_control=2026-04-01 | semana_control = **1** | Media |
| TC-060-06 | Permisos | Usuario perfil Auditor autenticado | Intentar crear/editar control | — | Acceso denegado; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Cálculo de semana del control con TC positivo y TC borde en verde
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar con Coordinación si la fecha base para el cálculo es la fecha de ingreso del paciente o la fecha del primer control médico (PCM).
- El perfil Clínico no usa el sistema (D1): los datos clínicos provienen de SALUTEM/SAM; aquí solo se registra el dato administrativo del control.

---

## [CEPA-061] Programación del próximo control y estado de agenda

**Épica:** EPIC-06 — Controles Médicos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.6
**Trazabilidad:** PRD §7.6.2 · §7.11 (alerta de próximo control) · Decisiones v4: D1, D12

### Historia
Como **Administrativo**, quiero **programar el día del próximo control y registrar si quedó agendado en el sistema de fichas clínicas** para **asegurar la continuidad del seguimiento del paciente y disparar alertas oportunas de próximos controles**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que existe un control médico registrado para un folio
  - **Cuando** el administrativo ingresa el **día del próximo control** y guarda
  - **Entonces** el sistema almacena la fecha del próximo control asociada al folio.
- **CA-2**
  - **Dado** que el administrativo programa un próximo control
  - **Cuando** indica el **estado de agenda en el sistema de fichas (agendado: sí/no)**
  - **Entonces** el sistema persiste el estado de agenda; por defecto el valor es "no" hasta que se confirme la agenda en SALUTEM/SAM.
- **CA-3**
  - **Dado** que un próximo control está programado dentro de la ventana de alerta configurada
  - **Cuando** el sistema ejecuta su revisión programada de alertas
  - **Entonces** se genera una alerta in-app visible para el administrativo asignado (referencia EPIC-10 / PRD §7.11).
- **CA-4**
  - **Dado** que el administrativo ingresa un día de próximo control anterior a la fecha del control actual
  - **Cuando** intenta guardar
  - **Entonces** el sistema rechaza el valor e informa que el próximo control debe ser posterior al control actual.

### Reglas de Negocio
- **RN-1:** El día del próximo control debe ser **posterior** a la fecha del control actual.
- **RN-2:** El estado de agenda (`agendado`) es booleano sí/no, con valor por defecto **no**. El sistema **no escribe** sobre SALUTEM/SAM (Decisiones v4 · D12); el estado se registra manualmente por el administrativo.
- **RN-3 (Alerta):** Cuando `próximo_control` entra en la ventana de alerta (referencia EPIC-10), se genera una alerta in-app. La alerta es independiente del estado de agenda (se alerta aunque `agendado=no` para que el administrativo agende).
- **RN-4:** Un folio puede tener a lo más **un** próximo control vigente programado a la vez; programar uno nuevo reemplaza/cierra el anterior pendiente.
- **RN-5 (Permisos):** Coordinación y Administrativo pueden programar/editar; Auditor solo lectura.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-061-01 | Positivo | Control registrado para folio 1024 | Ingresar día de próximo control y agendado=sí; guardar | próximo=2026-03-15, agendado=sí | Próximo control y estado agendado persistidos | Alta |
| TC-061-02 | Positivo | Próximo control dentro de ventana de alerta | Ejecutar proceso de alertas | próximo en 2 días, agendado=no | Alerta in-app generada para el administrativo asignado | Alta |
| TC-061-03 | Negativo | Control actual=2026-03-01 | Ingresar próximo control anterior y guardar | próximo=2026-02-20 | Bloqueo: próximo control debe ser posterior | Alta |
| TC-061-04 | Borde | Sin agendar aún | Guardar próximo control sin marcar agenda | agendado vacío | Sistema asume agendado=**no** por defecto | Media |
| TC-061-05 | Borde | Folio con un próximo control pendiente | Programar un nuevo próximo control | nuevo=2026-04-01 | El próximo control pendiente anterior se cierra/reemplaza | Media |
| TC-061-06 | Permisos | Usuario perfil Auditor autenticado | Intentar programar próximo control | — | Acceso denegado; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Generación de alerta de próximo control verificada (integración con EPIC-10)
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- La lógica y ventana exacta de la alerta de próximo control se especifica en **EPIC-10 — Alertas y Tareas** (PRD §7.11). Aquí solo se modela el dato disparador.
- Confirmar la ventana de anticipación de la alerta (¿días hábiles / corridos?) con Coordinación.

---

## [CEPA-062] Licencias y RECA asociadas al control

**Épica:** EPIC-06 — Controles Médicos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.6
**Trazabilidad:** PRD §7.6.3 · §7.6.4 · Decisiones v4: D1, D8

### Historia
Como **Administrativo**, quiero **registrar la licencia médica asociada al control (término, total de días, tipo, reposo, GAF) y el estado RECA con observaciones** para **consolidar en el control toda la información de seguimiento administrativo del paciente sin recurrir a planillas separadas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un control médico marca **Licencia = sí**
  - **Cuando** el administrativo ingresa resumen de término de LM, total de días de LM, tipo de licencia, tipo de reposo y GAF, y guarda
  - **Entonces** el sistema persiste estos datos asociados al control.
- **CA-2**
  - **Dado** que un control marca **Licencia = no**
  - **Cuando** se guarda el control
  - **Entonces** el sistema no exige los campos de licencia y los deja vacíos/no aplica.
- **CA-3**
  - **Dado** que se ingresa el GAF
  - **Cuando** el valor está fuera del rango 0–100
  - **Entonces** el sistema rechaza el valor e informa el rango válido.
- **CA-4**
  - **Dado** que el administrativo registra el **estado RECA** y **observaciones generales**
  - **Cuando** guarda el control
  - **Entonces** el sistema persiste el estado RECA y las observaciones, visibles en la vista de gestión de controles y para el Auditor.

### Reglas de Negocio
- **RN-1:** Si `licencia = sí`, los campos resumen de término de LM, total de días de LM, tipo de licencia y tipo de reposo son **obligatorios**. Si `licencia = no`, se omiten.
- **RN-2:** `tipo_reposo` ∈ {total, parcial}. `total_días_LM` es entero ≥ 1.
- **RN-3:** `GAF` (GAF/EEAG) es entero en rango **0–100**; valores fuera de rango se rechazan.
- **RN-4:** `tipo_licencia` toma valores del catálogo de tipos de LM (ej. tipo 1, 5, 6 — consistente con §7.7.1).
- **RN-5:** El estado RECA y las observaciones generales son siempre editables independientemente del valor de `licencia`.
- **RN-6 (Permisos):** Coordinación y Administrativo editan; Auditor solo lectura (sin edición de datos — PRD §5.3).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-062-01 | Positivo | Control existente con licencia=sí | Completar datos de LM y GAF; guardar | total_días=15, tipo_reposo=total, tipo_licencia=1, GAF=55 | Datos de licencia y GAF persistidos en el control | Alta |
| TC-062-02 | Positivo | Control existente | Registrar estado RECA y observaciones; guardar | estado_RECA="Pendiente", obs="Reevaluar en próximo control" | Estado RECA y observaciones persistidos y visibles para Auditor | Alta |
| TC-062-03 | Negativo | Control con licencia=sí | Guardar sin total de días ni tipo de reposo | campos LM vacíos | Bloqueo: campos de licencia obligatorios | Alta |
| TC-062-04 | Negativo | Control con GAF informado | Ingresar GAF fuera de rango y guardar | GAF=120 | Error: GAF debe estar entre 0 y 100; no persiste | Alta |
| TC-062-05 | Borde | Control con licencia=no | Guardar sin datos de LM | licencia=no | Guardado correcto; campos de LM vacíos/no aplica | Media |
| TC-062-06 | Permisos | Usuario perfil Auditor autenticado | Intentar editar licencia/RECA del control | — | Acceso denegado; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Validación de rango GAF (0–100) y obligatoriedad condicional de LM en verde
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- La licencia registrada aquí es un **resumen** asociado al control; el módulo de Licencias Médicas (§7.7 / EPIC futura) es la fuente de verdad del detalle y de los días acumulados. Confirmar si este resumen se deriva automáticamente de ese módulo o se digita aparte.
- Contemplar licencias médicas **extra-sistema** (Decisiones v4 · D7) en el catálogo de tipo de licencia.
