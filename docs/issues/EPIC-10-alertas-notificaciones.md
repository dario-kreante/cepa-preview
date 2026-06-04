# EPIC-10 — Alertas y Notificaciones

**Módulos PRD:** §7.11 (Alertas y Tareas Automatizadas) · §7.12 (Notificaciones y Comunicación)
**Prioridad de la épica:** P0 Must
**Perfiles operativos:** Coordinación · Administrativo · Auditor (NO Clínico — ver Decisiones v4 D1)
**Decisiones v4 aplicables:** D1 (sin perfil Clínico) · D3 (ODAS) · D12 (correo solo para alertas)

> Sistema de notificaciones y alertas con plazos perentorios que garantiza el objetivo
> institucional **OU4: 0% de vencimientos de licencia, control o informe sin alerta previa**.
> Las alertas se generan mediante una revisión programada (job) y se exponen en un panel
> in-app por rol; el correo electrónico se usa **solo para alertas** vía SMTP institucional.
> WhatsApp queda **fuera de alcance v1** (P2, sin WABA — ver PRD §7.12 y No-Objetivos).

## Historias

| ID | Título | Perfil | Prioridad | Módulo |
|----|--------|--------|-----------|--------|
| CEPA-100 | Motor de alertas con plazos perentorios | Administrativo | P0 Must | §7.11 |
| CEPA-101 | Panel de notificaciones in-app por rol | Coordinación / Administrativo / Auditor | P0 Must | §7.12 |
| CEPA-102 | Notificaciones por correo (solo alertas) | Sistema | P1 Should | §7.12 |
| CEPA-103 | Tareas pendientes por rol | Administrativo / Coordinación | P1 Should | §7.11 |

---

## [CEPA-100] Motor de alertas con plazos perentorios

**Épica:** EPIC-10 — Alertas y Notificaciones
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.11
**Trazabilidad:** PRD §7.11 · §7.2.5 · §7.7.4 · §7.3.3 · §7.6 · OU4 · Decisiones v4: D3

### Historia
Como **administrativo del CEPA**, quiero que el sistema **detecte automáticamente, mediante una revisión programada, todos los plazos perentorios próximos a vencer y genere alertas** para **no depender de mi memoria ni de revisar planillas a diario y lograr 0% de vencimientos sin alerta previa**.

### Criterios de Aceptación (Gherkin)
- **CA-1 (próximo control médico)**
  - **Dado** un paciente con un control médico programado dentro de la ventana de aviso configurada
  - **Cuando** el job de revisión de alertas se ejecuta
  - **Entonces** se genera una alerta de "próximo control médico" para el administrativo asignado al caso
- **CA-2 (vencimiento de licencia médica)**
  - **Dado** una licencia médica que vence dentro de los próximos 3 días hábiles
  - **Cuando** el job ejecuta la revisión programada
  - **Entonces** se genera una alerta de "vencimiento de licencia médica" visible para el administrativo asignado
- **CA-3 (plazos de informe EPT y entrega ISL)**
  - **Dado** un caso EPT con plazo de informe EPT o de entrega ISL dentro de la ventana de aviso
  - **Cuando** el job se ejecuta
  - **Entonces** se genera una alerta de "plazo EPT/ISL por vencer" para el funcionario administrativo a cargo del EPT
- **CA-4 (cumplimiento de protocolos — consentimiento informado)**
  - **Dado** un caso en estado de inicio de tratamiento sin consentimiento informado firmado registrado
  - **Cuando** el job se ejecuta
  - **Entonces** se genera una alerta de "consentimiento informado pendiente"
- **CA-5 (recetas por renovar/gestionar)**
  - **Dado** una receta con fecha de revisión dentro de los próximos 5 días
  - **Cuando** el job se ejecuta
  - **Entonces** se genera una alerta de "receta por renovar/gestionar" para el administrativo asignado
- **CA-6 (ODAS por vencer — v4 D3)**
  - **Dado** una ODA (Orden de Primera Atención) con fecha de vencimiento dentro de la ventana de aviso
  - **Cuando** el job se ejecuta
  - **Entonces** se genera una alerta de "ODA por vencer" para el administrativo asignado
- **CA-7 (sin duplicados / idempotencia)**
  - **Dado** una alerta ya generada y activa para un plazo concreto de un caso
  - **Cuando** el job se vuelve a ejecutar antes de que el plazo cambie o la alerta se resuelva
  - **Entonces** no se crea una alerta duplicada para el mismo plazo y caso
- **CA-8 (cobertura OU4)**
  - **Dado** cualquier plazo perentorio de los tipos soportados
  - **Cuando** llega su fecha de vencimiento
  - **Entonces** existe registro de que se generó al menos una alerta previa (0% de vencimientos sin alerta)

### Reglas de Negocio
- **RN-1:** Tipos de alerta soportados: próximo control médico, vencimiento de licencia médica, plazo de informe EPT, plazo de entrega ISL, consentimiento informado pendiente, receta por renovar/gestionar, ODA por vencer.
- **RN-2:** El job de revisión se ejecuta de forma **programada** (scheduled) en días hábiles, con ventana de mantenimiento nocturna respetada; la frecuencia es configurable (al menos una corrida diaria).
- **RN-3:** Cada tipo de alerta tiene una **ventana de aviso** parametrizable (ej. licencia 3 días hábiles, receta 5 días). Valores por defecto: licencia 3 días hábiles, receta 5 días; resto a configurar con CEPA.
- **RN-4:** **Idempotencia:** una misma combinación (caso, tipo de alerta, plazo objetivo) genera una sola alerta activa; el job no duplica alertas ya vigentes.
- **RN-5:** La alerta se **dirige al administrativo asignado** del caso/módulo correspondiente; Coordinación y Auditor pueden visualizar según su alcance (ver CEPA-101). El perfil Clínico no recibe alertas (D1).
- **RN-6:** Cada cálculo de plazo respeta **días hábiles** cuando el plazo regulatorio así lo define (licencias, EPT/ISL).
- **RN-7:** **Objetivo OU4:** 0% de vencimientos sin alerta previa; toda alerta generada y su resolución quedan trazadas para auditar el cumplimiento de este indicador.
- **RN-8:** La generación de alertas y su resolución se registran en el **log de auditoría** (OI1).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-100-01 | Positivo | Licencia que vence en 2 días hábiles, admin asignado | Ejecutar job de alertas | LM folio X, vencimiento +2d hábiles | Se crea 1 alerta "vencimiento LM" para el admin asignado | Alta |
| TC-100-02 | Positivo | ODA con vencimiento dentro de ventana | Ejecutar job | ODA vence +N días (D3) | Se crea alerta "ODA por vencer" | Alta |
| TC-100-03 | Positivo | Caso en inicio de tratamiento sin consentimiento firmado | Ejecutar job | Caso sin flag consentimiento | Se crea alerta "consentimiento informado pendiente" | Alta |
| TC-100-04 | Negativo | Licencia que vence en 30 días (fuera de ventana) | Ejecutar job | LM vencimiento +30d | No se genera alerta de vencimiento | Alta |
| TC-100-05 | Borde | Alerta ya activa para el mismo plazo y caso | Ejecutar job dos veces seguidas | Mismo (caso, tipo, plazo) | No se crea alerta duplicada (idempotencia) | Media |
| TC-100-06 | Borde | Plazo cae en fin de semana / cálculo en días hábiles | Ejecutar job | LM vence viernes, ventana 3d hábiles | Alerta generada con cálculo correcto de días hábiles | Media |
| TC-100-07 | Permisos | Job programado sin sesión de usuario | Ejecutar job de sistema | Cuenta de servicio | El job corre sin requerir un usuario clínico; no se exponen alertas a perfil Clínico | Media |

### Definición de Hecho (DoD)
- [ ] Job programado de revisión de alertas implementado y desplegado en QA
- [ ] Los 7 tipos de alerta (incl. ODAS, D3) generan alertas correctamente
- [ ] Todos los CA verificados, incluida idempotencia (CA-7) y cobertura OU4 (CA-8)
- [ ] Tests unitarios + integración en verde (cálculo de plazos en días hábiles con TC borde)
- [ ] Endpoint(s) de gestión/consulta de alertas documentados en OpenAPI/Swagger
- [ ] Generación y resolución de alertas registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Ventanas de aviso por tipo de alerta a confirmar con Coordinación (valores por defecto propuestos en RN-3).
- D3 ODAS: confirmar campos de la ODA (registro, fecha de vencimiento) y su origen manual.
- D9: el origen del consentimiento firmado (validador) condiciona CA-4; se asume flag/adjunto disponible en el caso.

---

## [CEPA-101] Panel de notificaciones in-app por rol

**Épica:** EPIC-10 — Alertas y Notificaciones
**Perfil:** Coordinación | Administrativo | Auditor
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.12
**Trazabilidad:** PRD §7.12 (Notificaciones in-app) · §7.13 (RBAC) · Decisiones v4: D1

### Historia
Como **usuario del CEPA (Coordinación / Administrativo / Auditor)**, quiero **ver un panel de alertas dentro del sistema al iniciar sesión, filtrado según mi rol y mis pacientes/casos asignados**, para **atender los plazos críticos pendientes sin revisar planillas externas**.

### Criterios de Aceptación (Gherkin)
- **CA-1 (panel al iniciar sesión)**
  - **Dado** un usuario con alertas pendientes asignadas
  - **Cuando** inicia sesión en el sistema
  - **Entonces** ve un panel de notificaciones con sus alertas activas visible desde el inicio
- **CA-2 (visibilidad por rol y casos asignados)**
  - **Dado** un administrativo con casos asignados
  - **Cuando** abre el panel
  - **Entonces** solo ve las alertas de sus pacientes/casos asignados, no las de otros administrativos
- **CA-3 (Coordinación/Auditor — alcance ampliado)**
  - **Dado** un usuario Coordinación o Auditor
  - **Cuando** abre el panel
  - **Entonces** ve alertas según su alcance (lectura total / módulos correspondientes) sin capacidad de editar datos clínicos
- **CA-4 (marcar como leída/resuelta)**
  - **Dado** una alerta visible en el panel
  - **Cuando** el usuario la marca como leída o resuelta
  - **Entonces** la alerta cambia de estado y deja de contarse como pendiente, registrándose la acción
- **CA-5 (navegación al caso)**
  - **Dado** una alerta del panel
  - **Cuando** el usuario hace clic en ella
  - **Entonces** el sistema navega al caso/módulo de origen de la alerta

### Reglas de Negocio
- **RN-1:** El panel es **in-app (P0)** y se muestra al iniciar sesión; es la fuente principal de notificaciones (no depende de correo).
- **RN-2:** **Filtrado por rol y asignación:** cada usuario ve solo las notificaciones que le corresponden según su perfil RBAC y sus pacientes/casos asignados.
- **RN-3:** Perfiles habilitados: **Coordinación, Administrativo, Auditor**. El perfil **Clínico no existe** en el sistema (D1) y no recibe panel.
- **RN-4:** **Auditor** tiene visibilidad de lectura sin edición de datos clínicos (PRD §5.3 / §7.13).
- **RN-5:** Estados de notificación: pendiente / leída / resuelta. El cambio de estado se registra en log de auditoría.
- **RN-6:** El panel refleja las alertas generadas por CEPA-100; ambas comparten el mismo origen de datos.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-101-01 | Positivo | Admin con 3 alertas asignadas | Iniciar sesión y abrir panel | Usuario admin A | Ve sus 3 alertas pendientes al iniciar sesión | Alta |
| TC-101-02 | Positivo | Alerta pendiente en el panel | Marcar como resuelta | Alerta ID Y | Estado pasa a resuelta y deja de contar como pendiente | Alta |
| TC-101-03 | Permisos | Admin A y Admin B con casos distintos | Admin A abre panel | Casos de B asignados a B | Admin A NO ve las alertas de los casos de B | Alta |
| TC-101-04 | Permisos | Usuario Auditor | Abre panel e intenta editar dato clínico | Perfil Auditor | Ve alertas (lectura) pero no puede editar datos clínicos | Alta |
| TC-101-05 | Borde | Usuario sin alertas pendientes | Iniciar sesión | Usuario sin asignaciones activas | Panel se muestra vacío / estado "sin notificaciones" sin error | Media |
| TC-101-06 | Positivo | Alerta de un caso concreto | Clic en la alerta | Alerta vinculada a caso Z | Navega al caso/módulo de origen | Media |

### Definición de Hecho (DoD)
- [ ] Panel in-app implementado y desplegado en QA, visible al iniciar sesión
- [ ] Todos los CA verificados (filtrado por rol/asignación, cambio de estado, navegación)
- [ ] Tests unitarios + integración en verde, incluidos TC de permisos (RBAC)
- [ ] Endpoint(s) de consulta/actualización de notificaciones documentados en OpenAPI/Swagger
- [ ] Cambios de estado de notificación registrados en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir alcance exacto de visibilidad de Coordinación vs. Auditor (lectura total vs. solo módulos de auditoría).
- Confirmar si la asignación de caso a administrativo es por módulo o por paciente (afecta RN-2).

---

## [CEPA-102] Notificaciones por correo (solo alertas)

**Épica:** EPIC-10 — Alertas y Notificaciones
**Perfil:** Sistema
**Prioridad (MoSCoW):** P1 Should
**Módulo PRD:** 7.12
**Trazabilidad:** PRD §7.12 (Correo electrónico) · PA6 · Decisiones v4: D12

### Historia
Como **sistema**, quiero **enviar por correo electrónico las alertas a los usuarios responsables vía el SMTP institucional de la Universidad de Talca**, para **reforzar la notificación in-app y reducir el riesgo de que un plazo crítico pase desapercibido**.

### Criterios de Aceptación (Gherkin)
- **CA-1 (envío de alerta por correo)**
  - **Dado** una alerta generada por el motor (CEPA-100) para un usuario con correo registrado
  - **Cuando** el sistema procesa el envío de notificaciones
  - **Entonces** envía un correo con el contenido de la alerta vía SMTP institucional al usuario responsable
- **CA-2 (solo alertas — D12)**
  - **Dado** cualquier evento del sistema que no sea una alerta de plazo perentorio
  - **Cuando** el sistema evalúa enviar correo
  - **Entonces** NO se envía correo (el canal email se usa exclusivamente para alertas)
- **CA-3 (dependencia de SMTP — PA6)**
  - **Dado** que el servicio SMTP institucional no está disponible o no confirmado
  - **Cuando** el sistema intenta enviar
  - **Entonces** la funcionalidad se degrada de forma controlada (la alerta in-app sigue funcionando) y el fallo de envío queda registrado
- **CA-4 (reintento / no duplicado)**
  - **Dado** un correo de alerta ya enviado correctamente
  - **Cuando** el proceso de envío se vuelve a ejecutar
  - **Entonces** no se reenvía el mismo correo de alerta de forma duplicada

### Reglas de Negocio
- **RN-1:** **El correo electrónico se usa SOLO para alertas** (D12). No se envían recordatorios/confirmaciones de citas por correo en v1.
- **RN-2:** El envío usa el **SMTP institucional de la UTalca**; depende de la confirmación de disponibilidad del servicio (**PA6**, bloqueante para esta historia).
- **RN-3:** El correo es **complementario** al panel in-app (CEPA-101), que es el canal P0; la indisponibilidad de correo no debe degradar la notificación in-app.
- **RN-4:** Cada envío (éxito/fallo) se registra para trazabilidad; los fallos no bloquean la generación de alertas.
- **RN-5:** **WhatsApp queda fuera de alcance (P2)** por ausencia de WABA; la arquitectura se diseña para soportar canales adicionales a futuro.
- **RN-6:** Solo reciben correo los perfiles operativos (Coordinación/Administrativo/Auditor) con correo válido; el perfil Clínico no aplica (D1).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-102-01 | Positivo | Alerta generada, SMTP disponible, usuario con correo | Procesar envío | Alerta + correo válido | Se envía correo de alerta vía SMTP institucional | Alta |
| TC-102-02 | Negativo | Evento que no es alerta (ej. confirmación de cita) | Procesar envío | Evento no-alerta | No se envía correo (D12) | Alta |
| TC-102-03 | Negativo | SMTP no disponible | Procesar envío | SMTP caído | Envío falla de forma controlada, alerta in-app intacta, fallo registrado | Alta |
| TC-102-04 | Borde | Correo de alerta ya enviado | Reejecutar proceso de envío | Misma alerta | No se reenvía duplicado | Media |
| TC-102-05 | Permisos | Usuario sin correo válido registrado | Procesar envío | Usuario sin email | No se envía correo; alerta in-app permanece disponible | Media |

### Definición de Hecho (DoD)
- [ ] Integración con SMTP institucional implementada y desplegada en QA (sujeta a PA6)
- [ ] Todos los CA verificados, incluida la restricción "solo alertas" (CA-2, D12)
- [ ] Tests unitarios + integración en verde (incl. degradación controlada por SMTP caído)
- [ ] Envíos (éxito/fallo) registrados para trazabilidad
- [ ] Plantillas de correo de alerta revisadas con CEPA
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- **PA6 (bloqueante):** confirmar disponibilidad del servicio SMTP institucional o necesidad de proveedor externo. Hasta su confirmación, esta historia permanece como P1 dependiente.
- D12: dejar explícito en arquitectura que email = solo alertas; canales futuros (WhatsApp P2) sin implementar.

---

## [CEPA-103] Tareas pendientes por rol

**Épica:** EPIC-10 — Alertas y Notificaciones
**Perfil:** Administrativo | Coordinación
**Prioridad (MoSCoW):** P1 Should
**Módulo PRD:** 7.11
**Trazabilidad:** PRD §7.11 (Tareas pendientes asignadas por rol) · §7.13 (RBAC) · Decisiones v4: D1

### Historia
Como **administrativo / coordinación del CEPA**, quiero **ver y gestionar mis tareas pendientes asignadas según mi rol**, para **organizar mi trabajo diario y no perder de vista las acciones operativas requeridas en cada caso**.

### Criterios de Aceptación (Gherkin)
- **CA-1 (lista de tareas por rol)**
  - **Dado** un usuario con tareas pendientes asignadas a su rol
  - **Cuando** accede a su sección de tareas pendientes
  - **Entonces** ve la lista de tareas que le corresponden según su perfil y asignación
- **CA-2 (completar tarea)**
  - **Dado** una tarea pendiente
  - **Cuando** el usuario la marca como completada
  - **Entonces** la tarea cambia de estado y deja de aparecer entre las pendientes, registrándose quién y cuándo
- **CA-3 (segregación por rol/asignación)**
  - **Dado** dos usuarios con tareas distintas
  - **Cuando** cada uno abre su lista
  - **Entonces** cada uno ve solo sus tareas, no las del otro
- **CA-4 (coordinación — vista ampliada)**
  - **Dado** un usuario de Coordinación
  - **Cuando** abre tareas pendientes
  - **Entonces** puede ver el estado de tareas del equipo según su alcance de supervisión

### Reglas de Negocio
- **RN-1:** Las tareas se **asignan por rol** y por usuario/caso; cada usuario ve las suyas (RBAC, PRD §7.13).
- **RN-2:** Perfiles aplicables: **Administrativo** (operación) y **Coordinación** (supervisión). El perfil Clínico no existe (D1).
- **RN-3:** Estados de tarea: pendiente / completada (y opcionalmente en progreso). El cambio de estado se registra en log de auditoría.
- **RN-4:** Las tareas pueden originarse de procesos operativos (ej. gestionar receta, enviar informe) y conviven con las alertas del motor (CEPA-100) sin duplicar su semántica de plazo.
- **RN-5:** Coordinación puede tener vista de supervisión del estado de tareas del equipo según su alcance.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-103-01 | Positivo | Admin con tareas asignadas | Abrir lista de tareas pendientes | Usuario admin A | Ve sus tareas pendientes según su rol | Alta |
| TC-103-02 | Positivo | Tarea pendiente | Marcar como completada | Tarea ID T | Tarea pasa a completada y sale de pendientes; queda registro | Alta |
| TC-103-03 | Permisos | Admin A y Admin B con tareas distintas | Admin A abre su lista | Tareas de B | Admin A no ve las tareas de B | Alta |
| TC-103-04 | Positivo | Coordinación supervisando equipo | Abrir vista de tareas | Perfil Coordinación | Ve estado de tareas del equipo según alcance | Media |
| TC-103-05 | Borde | Usuario sin tareas pendientes | Abrir lista | Usuario sin asignaciones | Lista vacía sin error | Media |

### Definición de Hecho (DoD)
- [ ] Gestión de tareas pendientes por rol implementada y desplegada en QA
- [ ] Todos los CA verificados (lista por rol, completar, segregación, vista coordinación)
- [ ] Tests unitarios + integración en verde, incluidos TC de permisos (RBAC)
- [ ] Endpoint(s) de tareas documentados en OpenAPI/Swagger
- [ ] Cambios de estado de tarea registrados en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir el catálogo de tipos de tarea operativa y su origen (manual vs. derivado de procesos de cada módulo).
- Confirmar alcance de la vista de supervisión de Coordinación (todo el equipo vs. su unidad).

---

## Notas de la épica
- **WhatsApp (P2 — fuera de alcance v1):** CEPA no dispone de cuenta WABA; el canal se diseña como extensible a futuro pero no se implementa en v1 (PRD §7.12, No-Objetivos).
- **Perfiles:** solo Coordinación, Administrativo y Auditor (Decisiones v4 D1). El perfil Clínico fue eliminado del sistema y no recibe alertas, panel, correo ni tareas.
- **OU4** es el objetivo medible de la épica: 0% de vencimientos sin alerta previa; CEPA-100 es la historia que lo sostiene.
- **Dependencias:** CEPA-101 y CEPA-102 consumen las alertas producidas por CEPA-100. CEPA-102 depende además de PA6 (SMTP institucional).
