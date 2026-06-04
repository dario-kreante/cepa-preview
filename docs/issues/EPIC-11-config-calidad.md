# EPIC-11 — Configurabilidad y Calidad de Datos

**Módulo PRD:** §7.13 Configurabilidad y Control de Acceso
**Prioridad (MoSCoW):** P0 Must (CEPA-110, CEPA-111) · P1 Should (CEPA-112)
**Perfiles:** Coordinación · Administrativo · Auditor (sin perfil Clínico — ver Decisiones v4 D1)

> **Alcance de esta épica:** configurabilidad autónoma de formularios, validación de
> parametrización / calidad de datos y lectura de documentos PDF.
>
> **Fuera de alcance (ver EPIC-00):** el **RBAC** (permisos edición vs. solo lectura por perfil)
> y el **log de auditoría** (quién modificó qué dato y cuándo) son requisitos transversales
> de §7.13 que se desarrollan en **EPIC-00**. En esta épica se **referencian**, no se duplican:
> toda historia consume el control de permisos y emite eventos de auditoría provistos por EPIC-00.

---

## [CEPA-110] Formularios dinámicos / campos configurables

**Épica:** EPIC-11 — Configurabilidad y Calidad de Datos
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.13
**Trazabilidad:** PRD §7.13 (configuración autónoma) · Historia de usuario §6.3 · Decisiones v4: D6

### Historia
Como **coordinadora del CEPA**, quiero **agregar, modificar o quitar campos en los formularios del sistema sin intervención del desarrollador** para **adaptar la plataforma a cambios normativos o de proceso sin depender de un ticket de desarrollo**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora está en el editor de formularios de un módulo
  - **Cuando** agrega un campo nuevo (define etiqueta, tipo de dato, obligatoriedad y orden) y publica
  - **Entonces** el campo aparece en el formulario operativo y queda disponible para captura sin necesidad de despliegue de código.
- **CA-2**
  - **Dado** un campo no obligatorio existente en un formulario
  - **Cuando** la coordinadora lo elimina o desactiva y publica
  - **Entonces** el campo deja de mostrarse en nuevas capturas y los datos históricos del campo se conservan (no se borran).
- **CA-3**
  - **Dado** un formulario con campos configurados
  - **Cuando** la coordinadora reordena o cambia el tipo de un campo y guarda como borrador
  - **Entonces** los cambios no afectan el formulario en producción hasta que la coordinadora publique la nueva versión.
- **CA-4**
  - **Dado** un usuario sin perfil Coordinación (Administrativo o Auditor)
  - **Cuando** intenta acceder al editor de formularios
  - **Entonces** el sistema deniega el acceso (control RBAC provisto por EPIC-00).

### Reglas de Negocio
- **RN-1:** La configuración de formularios es exclusiva del perfil **Coordinación** (autorización delegada a EPIC-00 RBAC).
- **RN-2:** Cada cambio publicado genera una **nueva versión** del formulario; las capturas previas mantienen la versión con que se crearon (versionado, sin pérdida de datos históricos).
- **RN-3:** Quitar o desactivar un campo **no elimina** los datos ya capturados en ese campo.
- **RN-4:** Todo cambio de configuración (alta/baja/modificación de campo, publicación) se registra en el **log de auditoría** de EPIC-00 (quién, qué, cuándo).
- **RN-5:** No se permite publicar un formulario que no pase la validación de parametrización (ver CEPA-111, RN-1).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-110-01 | Positivo | Coordinación en editor del módulo Ingresos | Agregar campo, definir tipo y obligatoriedad, publicar | Campo "Comuna" (texto, obligatorio) | El campo aparece en el formulario operativo; nueva versión publicada | Alta |
| TC-110-02 | Positivo | Existe campo opcional "Observación extra" | Desactivar el campo y publicar | — | El campo deja de capturarse; datos históricos conservados | Alta |
| TC-110-03 | Negativo | Coordinación en editor con borrador inválido | Intentar publicar formulario sin nomenclatura válida | Campo obligatorio sin nombre estándar | Publicación bloqueada con mensaje de error (enlaza CEPA-111) | Alta |
| TC-110-04 | Borde | Formulario v1 con 200 capturas históricas | Publicar v2 que quita un campo | — | Capturas v1 siguen mostrando el campo; v2 ya no lo captura | Media |
| TC-110-05 | Permisos | Usuario Administrativo autenticado | Intentar abrir el editor de formularios | — | Acceso denegado (HTTP 403) por RBAC EPIC-00 | Alta |
| TC-110-06 | Permisos | Usuario Auditor autenticado | Intentar publicar cambios en un formulario | — | Acceso denegado; Auditor es solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] Editor de formularios (CRUD de campos + versionado) implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) de configuración documentados en OpenAPI/Swagger
- [ ] Operaciones de configuración registradas en log de auditoría (EPIC-00)
- [ ] Control RBAC validado contra EPIC-00 (solo Coordinación)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Tipos de campo soportados en v1 (texto, número, fecha, selección, sí/no) pendiente de acordar con Coordinación.
- Integra con CEPA-111: la publicación pasa obligatoriamente por la validación de parametrización.

---

## [CEPA-111] Validación de parametrización y campos obligatorios

**Épica:** EPIC-11 — Configurabilidad y Calidad de Datos
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.13
**Trazabilidad:** PRD §7.13 · Decisiones v4: D6 (campos obligatorios y calidad de datos)

### Historia
Como **coordinadora del CEPA**, quiero **que el sistema valide técnicamente que un formulario modificado quede bien parametrizado y conserve los campos obligatorios bajo nomenclatura estándar** para **garantizar información limpia, fidedigna y comparable entre programas, profesionales y períodos**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora intenta publicar un formulario
  - **Cuando** la validación detecta un campo sin tipo de dato, sin nomenclatura válida o con configuración inconsistente
  - **Entonces** el sistema **bloquea la publicación** y muestra la lista de errores de parametrización a corregir.
- **CA-2**
  - **Dado** un formulario que contiene un **campo obligatorio del sistema** (sexo, edad, diagnóstico, modelo de tratamiento, tipos de alta, tipo de ingreso, tipo de convenio)
  - **Cuando** la coordinadora intenta quitar o desactivar dicho campo
  - **Entonces** el sistema **impide la acción** e informa que es un campo obligatorio no removible.
- **CA-3**
  - **Dado** un formulario con todos los campos obligatorios presentes y bien parametrizados
  - **Cuando** la coordinadora publica
  - **Entonces** la publicación se completa y el formulario queda marcado como **válido / bien parametrizado**.
- **CA-4**
  - **Dado** un campo obligatorio con un dominio cerrado (ej. tipo de ingreso, tipo de convenio)
  - **Cuando** un administrativo guarda un registro dejando ese campo vacío
  - **Entonces** el sistema rechaza el guardado e indica el campo obligatorio faltante.

### Reglas de Negocio
- **RN-1:** **No se permite publicar** un formulario mal parametrizado (campo sin tipo, sin etiqueta/nomenclatura estándar, obligatorio sin dominio definido o con duplicidad de identificador).
- **RN-2:** **No se permite quitar ni desactivar** del sistema un **campo obligatorio**: sexo, edad, diagnóstico, modelo de tratamiento, tipos de alta, tipo de ingreso, tipo de convenio (Decisiones v4 D6).
- **RN-3:** Los campos obligatorios usan **nomenclatura estandarizada** (identificador y dominio de valores controlados) para que la información sea comparable entre módulos y reportes.
- **RN-4:** En captura operativa, los campos marcados obligatorios no admiten valor vacío; los de dominio cerrado solo aceptan valores del catálogo definido.
- **RN-5:** Cada intento de publicación (exitoso o bloqueado) y cada intento de remoción de campo obligatorio se registran en el **log de auditoría** de EPIC-00.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-111-01 | Positivo | Formulario con los 7 campos obligatorios bien parametrizados | Publicar | sexo, edad, diagnóstico, modelo tto, tipo alta, tipo ingreso, tipo convenio | Publicación exitosa; formulario marcado "válido" | Alta |
| TC-111-02 | Negativo | Coordinación edita formulario | Agregar campo obligatorio sin tipo de dato y publicar | Campo "edad" sin tipo | Publicación bloqueada con detalle del error de parametrización | Alta |
| TC-111-03 | Negativo | Formulario con campo "diagnóstico" obligatorio | Intentar quitar/desactivar "diagnóstico" | — | Acción impedida: campo obligatorio no removible | Alta |
| TC-111-04 | Negativo | Administrativo en captura de ingreso | Guardar dejando "tipo de ingreso" vacío | tipo de ingreso = (vacío) | Guardado rechazado; mensaje de campo obligatorio | Alta |
| TC-111-05 | Borde | Campo "tipo de convenio" con dominio cerrado | Capturar un valor fuera del catálogo | valor no listado | Sistema rechaza valor fuera de dominio | Media |
| TC-111-06 | Permisos | Usuario Administrativo autenticado | Intentar modificar la parametrización de campos obligatorios | — | Acceso denegado por RBAC EPIC-00 (solo Coordinación) | Alta |

### Definición de Hecho (DoD)
- [ ] Motor de validación de parametrización implementado y desplegado en QA
- [ ] Catálogo de campos obligatorios y nomenclatura estándar definido y aplicado
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) de validación/publicación documentados en OpenAPI/Swagger
- [ ] Bloqueos y remociones impedidas registrados en log de auditoría (EPIC-00)
- [ ] Control RBAC validado contra EPIC-00
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar el **dominio de valores** definitivo de cada campo obligatorio de dominio cerrado (tipos de alta, tipo de ingreso, tipo de convenio) — coordinar con D4 (tipos de derivación) y D11 (tipificación de altas).
- Define la precondición de publicación de CEPA-110 (RN-5): ambas historias se entregan acopladas.

---

## [CEPA-112] Lectura de documentos PDF

**Épica:** EPIC-11 — Configurabilidad y Calidad de Datos
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P1 Should *(reclasificado desde P2 — Decisiones v4 D12)*
**Módulo PRD:** 7.13
**Trazabilidad:** PRD §7.13 (lectura automática de PDF) · Decisiones v4: D12

### Historia
Como **administrativo del CEPA**, quiero **cargar un documento PDF (ficha clínica, registro, datos sociodemográficos) y que el sistema extraiga automáticamente sus datos con posibilidad de editarlos antes de guardar** para **evitar la digitación manual y reducir errores de transcripción**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que el administrativo carga un PDF legible con datos sociodemográficos
  - **Cuando** el sistema procesa el documento
  - **Entonces** muestra los campos extraídos pre-llenados en el formulario, listos para revisión.
- **CA-2**
  - **Dado** un PDF con datos extraídos pre-llenados
  - **Cuando** el administrativo corrige uno o más valores y confirma
  - **Entonces** el sistema guarda los datos editados (la edición humana prevalece sobre la extracción automática).
- **CA-3**
  - **Dado** un archivo que no es PDF o un PDF ilegible/escaneado sin texto extraíble
  - **Cuando** el administrativo intenta cargarlo
  - **Entonces** el sistema informa que no pudo extraer datos y permite la captura manual sin bloquear el flujo.
- **CA-4**
  - **Dado** un usuario sin permiso de captura sobre el módulo destino
  - **Cuando** intenta cargar un PDF para extracción
  - **Entonces** el sistema deniega la acción (RBAC EPIC-00).

### Reglas de Negocio
- **RN-1:** La extracción de PDF es **asistencia, no autoridad**: todo dato extraído es **editable** y debe confirmarse por el administrativo antes de persistir.
- **RN-2:** El aplicativo **no escribe sobre SALUTEM/SAM** (Decisiones v4 D12); la lectura de PDF alimenta únicamente los módulos del Sistema CEPA.
- **RN-3:** Si la extracción falla o el PDF es ilegible, el sistema **degrada con gracia** a captura manual sin perder el documento cargado.
- **RN-4:** Los datos confirmados se validan contra las reglas de campos obligatorios y dominios (CEPA-111) antes de guardar.
- **RN-5:** La carga del documento y el guardado de los datos extraídos/editados se registran en el **log de auditoría** de EPIC-00.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-112-01 | Positivo | Administrativo con permiso de captura | Cargar PDF legible y procesar | PDF sociodemográfico con texto | Campos extraídos pre-llenados para revisión | Alta |
| TC-112-02 | Positivo | Datos extraídos pre-llenados | Editar un valor y confirmar guardado | Corrección de RUT | Se guarda el valor editado, no el extraído | Alta |
| TC-112-03 | Negativo | Administrativo carga archivo no PDF | Subir un .docx | archivo no soportado | Mensaje de formato no soportado; permite captura manual | Media |
| TC-112-04 | Borde | PDF escaneado sin capa de texto | Cargar y procesar | PDF imagen ilegible | Sistema informa extracción fallida y ofrece captura manual | Media |
| TC-112-05 | Negativo | Datos extraídos con campo obligatorio vacío | Confirmar guardado | "tipo de ingreso" no detectado | Guardado bloqueado por validación de CEPA-111 | Alta |
| TC-112-06 | Permisos | Usuario Auditor (solo lectura) | Intentar cargar PDF para extracción en un módulo | — | Acción denegada por RBAC EPIC-00 | Alta |

### Definición de Hecho (DoD)
- [ ] Carga + extracción de PDF con pre-llenado editable implementada y desplegada en QA
- [ ] Manejo de errores/degradación a captura manual verificado
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) de carga/extracción documentados en OpenAPI/Swagger
- [ ] Validación de datos contra CEPA-111 integrada
- [ ] Carga y guardado registrados en log de auditoría (EPIC-00)
- [ ] Control RBAC validado contra EPIC-00
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Reclasificada de **P2 a P1** por Decisiones v4 D12.
- Definir el **conjunto de tipos de documento** soportados en v1 y su mapeo de campos (fichas clínicas, registros, datos sociodemográficos).
- Confirmar si se requiere OCR para PDF escaneados o si v1 se limita a PDF con capa de texto.
