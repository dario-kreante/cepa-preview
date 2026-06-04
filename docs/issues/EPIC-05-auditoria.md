# EPIC-05 — Auditoría

**Módulo PRD:** §7.5 — Módulo de Auditoría
**Prioridad (MoSCoW):** P0 Must
**Reemplaza:** hoja Excel «Auditoría» (28 columnas)
**Objetivo:** proveer una **vista consolidada de fiscalización** que reúne en una sola pantalla todos los hitos de cada caso clínico —datos del caso, seguimiento de evaluaciones, controles y tratamiento, y cierre— para verificar el cumplimiento de protocolos **sin cruzar manualmente las 7 planillas**, y generar reportes de auditoría filtrables, verificables, trazables y descargables para las instituciones contraparte.

**Perfiles operativos (RBAC):** Coordinación · Administrativo · Auditor. **El perfil Clínico NO accede al sistema** (Decisiones v4 · D1): el clínico registra en SALUTEM/SAM. El perfil **Auditor** tiene **lectura total y módulo de auditoría SIN edición de datos clínicos**; **Coordinación** tiene lectura total; **Administrativo** mantiene la captura de datos en los módulos de origen (Ingresos, Fármacos, Reintegro, Controles, Licencias). La auditoría es **consolidación de solo lectura**: no crea ni modifica datos clínicos, los lee de los módulos fuente.

## Glosario de la épica
| Término | Definición |
|---------|------------|
| **RECA** | Resolución de Calificación: documento de la mutualidad/ISL que califica el origen (enfermedad profesional / accidente del trabajo) y los riesgos del caso. El diagnóstico puede variar entre el inicial y el post-RECA. |
| **Siniestro (Nº de siniestro)** | Identificador del evento denunciado. Permite diferenciar varias denuncias bajo un mismo RUT (ej. DIAT 2020 y DIEP 2026 — D2). |
| **Alta** | Cierre de una dimensión del caso: alta médica, alta psicológica o alta terapéutica. Marca el fin de la prestación correspondiente. |
| **GAF / EEAG** | Escala de Evaluación de la Actividad Global (Global Assessment of Functioning): puntaje de funcionamiento global del usuario. |

## Historias de la épica
| ID | Título | Perfil | PRD |
|----|--------|--------|-----|
| CEPA-050 | Vista consolidada del caso con todos sus hitos | Auditor | §7.5.1–§7.5.4 |
| CEPA-051 | Reportes de auditoría con filtros | Auditor | §6.4 / §7.9 |

---

## [CEPA-050] Vista consolidada del caso con todos sus hitos

**Épica:** EPIC-05 — Auditoría
**Perfil:** Auditor
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.5.1, 7.5.2, 7.5.3, 7.5.4
**Trazabilidad:** PRD §7.5.1 · §7.5.2 · §7.5.3 · §7.5.4 · §7.10 · Decisiones v4: D1, D2, D11 · Log de auditoría: EPIC-00

**Campos (consolidados en solo lectura desde los módulos fuente):**

*§7.5.1 Datos del caso*
- Folio (vinculado al módulo de Ingresos)
- Número de siniestro (diferencia denuncias bajo un mismo RUT — D2)
- Fecha de denuncia y tipo de denuncia
- Fecha de derivación
- Nombre completo del usuario · RUT · Región

*§7.5.2 Seguimiento de evaluaciones*
- Fecha de evaluación médica · Fecha de evaluación psicológica
- Fecha de calificación (RECA)
- Diagnóstico inicial · Diagnóstico post-RECA
- Número de sesiones (de evaluación)

*§7.5.3 Controles y tratamiento*
- Fecha de 1ª consulta médica de tratamiento · Fecha de 1ª consulta psicológica de tratamiento
- Nº de sesiones médicas · Nº de sesiones psicológicas · Nº de sesiones de ampliación de tratamiento
- Reintegro parcial (sí/no + fecha) · Reintegro total (sí/no + fecha)

*§7.5.4 Cierre*
- Alta médica · Alta psicológica · Alta terapéutica (sí/no + fecha)
- Estado general del caso
- Observaciones

### Historia
Como **Auditor**, quiero **abrir una vista consolidada de cada caso con todos sus hitos (datos del caso, evaluaciones, calificación, diagnósticos inicial y post-RECA, controles y sesiones, reintegro parcial/total y altas)** para **verificar el cumplimiento de protocolos sin cruzar manualmente las 7 planillas y sin editar datos clínicos**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un Auditor busca un caso por folio, RUT o número de siniestro
  - **Cuando** abre la vista consolidada de auditoría
  - **Entonces** el sistema muestra en una sola pantalla los datos del caso (§7.5.1), el seguimiento de evaluaciones (§7.5.2), los controles y tratamiento (§7.5.3) y el cierre (§7.5.4), consolidados desde los módulos de origen.
- **CA-2**
  - **Dado** que un usuario tiene dos denuncias bajo el mismo RUT con distinto número de siniestro (ej. DIAT 2020 y DIEP 2026 — D2)
  - **Cuando** el Auditor abre la vista consolidada
  - **Entonces** cada siniestro se presenta como un caso diferenciado y no se mezclan sus hitos.
- **CA-3**
  - **Dado** que un caso tiene diagnóstico inicial y diagnóstico post-RECA distintos
  - **Cuando** el Auditor revisa el seguimiento de evaluaciones
  - **Entonces** el sistema muestra ambos diagnósticos por separado junto con la fecha de calificación.
- **CA-4**
  - **Dado** un Auditor situado en la vista consolidada de un caso
  - **Cuando** intenta modificar cualquier dato clínico (diagnóstico, sesiones, fechas, altas)
  - **Entonces** el sistema no ofrece controles de edición y la acción queda denegada (vista de solo lectura).
- **CA-5**
  - **Dado** un caso aún en tratamiento sin altas registradas
  - **Cuando** el Auditor abre la vista consolidada
  - **Entonces** las secciones de cierre (§7.5.4) se muestran como pendientes/vacías sin bloquear la visualización del resto de los hitos.

### Reglas de Negocio
- **RN-1:** La vista de auditoría es **consolidación de solo lectura**: lee datos de Ingresos, Fármacos, Reintegro, Controles y Licencias; **no crea ni modifica datos clínicos**.
- **RN-2:** **El Auditor no puede editar datos clínicos** (D1 · PRD §5.3): el perfil tiene lectura total y módulo de auditoría sin edición.
- **RN-3:** El folio es la clave de consolidación; el caso siempre pertenece a un folio existente. El **número de siniestro** diferencia denuncias múltiples bajo un mismo RUT (D2).
- **RN-4:** Diagnóstico inicial y diagnóstico post-RECA se almacenan y muestran por separado; la fecha de calificación es la de la RECA asociada.
- **RN-5:** Coherencia temporal de hitos: fecha de denuncia ≤ fecha de derivación ≤ fechas de evaluación ≤ fecha de calificación ≤ 1ª consulta de tratamiento ≤ fechas de alta (validación heredada de los módulos fuente; la auditoría señala inconsistencias, no las corrige).
- **RN-6:** El cierre (§7.5.4) puede tener altas parciales (solo médica, solo psicológica) o terapéutica; la simplificación de una sola fecha de alta queda sujeta a D11 (pendiente de confirmar con Coordinación).
- **RN-7:** El acceso a la vista consolidada se registra en el **log de auditoría** (EPIC-00): quién consultó qué caso y cuándo. Solo perfiles Coordinación y Auditor acceden; Administrativo accede según permisos de sus módulos.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-050-01 | Positivo | Caso con datos en todos los módulos | Buscar por folio y abrir vista consolidada | Folio 2026-0123 | Pantalla única con §7.5.1–§7.5.4 consolidados desde los módulos fuente | Alta |
| TC-050-02 | Positivo | Usuario con 2 siniestros bajo el mismo RUT | Abrir vista consolidada por RUT | DIAT 2020 + DIEP 2026 | Dos casos diferenciados por nº de siniestro, sin mezclar hitos | Alta |
| TC-050-03 | Positivo | Caso con diagnóstico inicial ≠ post-RECA | Revisar seguimiento de evaluaciones | Dx inicial / Dx post-RECA | Ambos diagnósticos y fecha de calificación visibles por separado | Media |
| TC-050-04 | Borde | Caso en tratamiento sin altas | Abrir vista consolidada | Sin §7.5.4 | Cierre mostrado como pendiente/vacío; resto de hitos visible sin error | Media |
| TC-050-05 | Negativo | Sesión Auditor en vista consolidada | Intentar editar diagnóstico/sesiones/altas | — | Sin controles de edición; acción denegada (solo lectura, RN-2) | Alta |
| TC-050-06 | Permisos | Sesión con perfil sin acceso a auditoría | Intentar abrir la vista consolidada | — | Acceso denegado por RBAC; consulta registrada/denegada en log (RN-7) | Alta |

### Definición de Hecho (DoD)
- [ ] Vista consolidada implementada (solo lectura) y desplegada en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) de consulta documentados en OpenAPI/Swagger
- [ ] Acceso/consulta registrado en log de auditoría (EPIC-00)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- D11: confirmar con Coordinación si el cierre usa una sola fecha de alta (última atención) o fechas separadas para alta médica, psicológica y terapéutica.
- D2: confirmar si la consolidación agrupa por folio + número de siniestro o si reingresos que mantienen folio se presentan como un solo caso con sub-hitos.
- Definir el origen de cada campo consolidado (mapeo módulo→dimensión) para garantizar fuente única de verdad y evitar discrepancias entre planillas digitalizadas.

---

## [CEPA-051] Reportes de auditoría con filtros

**Épica:** EPIC-05 — Auditoría
**Perfil:** Auditor
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.5 / 7.9
**Trazabilidad:** PRD §6.4 (historia de Auditor) · §7.9 (Reportería) · §7.5 · Decisiones v4: D1, D5 · Reportería: EPIC-09 · Log de auditoría: EPIC-00

**Filtros / dimensiones:**
- Período (rango de fechas: diario, semanal, mensual, anual)
- Diagnóstico (inicial / post-RECA)
- Profesional (médico tratante, psicólogo, EPTista)
- Estado del caso (activo, cerrado, derivado, etc.)
- (Complementarios alineados a D5/§7.9: programa, tipo de alta, región/comuna, tipo de ingreso)

**Salida del reporte:**
- Datos verificables y trazables por caso (folio, nº siniestro, hitos)
- Descargable en formatos estándar (para instituciones contraparte)

### Historia
Como **Auditor**, quiero **generar reportes de auditoría filtrando por período, diagnóstico, profesional y estado del caso, con datos verificables y trazables y descargables** para **presentar informes precisos a las instituciones contraparte sin procesamiento manual de planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un Auditor abre el generador de reportes de auditoría
  - **Cuando** selecciona un período, un diagnóstico, un profesional y un estado del caso, y ejecuta
  - **Entonces** el sistema devuelve únicamente los casos que cumplen todos los filtros aplicados, con sus hitos consolidados.
- **CA-2**
  - **Dado** un reporte generado con filtros aplicados
  - **Cuando** el Auditor solicita la descarga
  - **Entonces** el sistema entrega el reporte en un formato estándar descargable, conservando los filtros aplicados como metadatos del reporte.
- **CA-3**
  - **Dado** un reporte de auditoría descargado
  - **Cuando** la institución contraparte verifica un dato
  - **Entonces** cada fila es trazable a su folio y número de siniestro de origen, permitiendo auditar el dato hasta su módulo fuente.
- **CA-4**
  - **Dado** una combinación de filtros sin casos coincidentes
  - **Cuando** el Auditor ejecuta el reporte
  - **Entonces** el sistema muestra un resultado vacío con mensaje claro, sin error y sin filas espurias.
- **CA-5**
  - **Dado** un perfil sin permiso de auditoría
  - **Cuando** intenta generar o descargar un reporte de auditoría
  - **Entonces** el sistema deniega la acción por RBAC.

### Reglas de Negocio
- **RN-1:** Los reportes son de **solo lectura**: el Auditor genera y descarga, **no edita datos clínicos** (D1 · PRD §5.3 — "Auditor no puede editar datos clínicos").
- **RN-2:** Los filtros son combinables (AND); un período es obligatorio para acotar el universo del reporte.
- **RN-3:** Cada fila del reporte es **trazable** a su folio + número de siniestro y, por ende, a su módulo fuente (datos verificables).
- **RN-4:** El reporte debe ser **descargable** en formato estándar para instituciones contraparte (alinear con §7.9 y la reportería de EPIC-09; este módulo aporta la dimensión de auditoría/cumplimiento).
- **RN-5:** La generación de cada reporte se registra en el **log de auditoría** (EPIC-00): quién generó qué reporte, con qué filtros y cuándo.
- **RN-6:** Filtros y dimensiones se alinean con las definiciones de dashboard/reportería (D5): diagnósticos, tipos de alta, profesional, programa, estado del caso, zona geográfica.
- **RN-7:** Solo Coordinación y Auditor generan/descargan reportes de auditoría; Auditor sin edición.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-051-01 | Positivo | Casos cargados en varios estados | Filtrar por período + diagnóstico + profesional + estado; ejecutar | Mayo 2026, Dx X, Dr. Y, Activo | Solo casos que cumplen todos los filtros, con hitos consolidados | Alta |
| TC-051-02 | Positivo | Reporte generado | Descargar el reporte | Formato estándar | Archivo descargado con filtros como metadatos | Alta |
| TC-051-03 | Positivo | Reporte descargado | Verificar trazabilidad de una fila | Folio + nº siniestro | Fila trazable hasta su módulo fuente | Media |
| TC-051-04 | Negativo | Filtros sin coincidencias | Ejecutar reporte con combinación imposible | Período sin casos | Resultado vacío con mensaje claro, sin error | Media |
| TC-051-05 | Borde | Período amplio (anual) con alto volumen | Ejecutar y descargar reporte anual | ~800 casos | Reporte paginado/completo en <2 s de respuesta y descarga íntegra | Media |
| TC-051-06 | Permisos | Sesión sin permiso de auditoría | Intentar generar/descargar reporte de auditoría | — | Acción denegada por RBAC (RN-7) | Alta |

### Definición de Hecho (DoD)
- [ ] Generación y descarga de reportes implementada (solo lectura) y desplegada en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) de reporte documentados en OpenAPI/Swagger
- [ ] Generación de reportes registrada en log de auditoría (EPIC-00)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir formatos de descarga estándar requeridos por las instituciones contraparte (CSV, XLSX, PDF) — coordinar con EPIC-09 (Reportería) para no duplicar el motor de reportes.
- Confirmar si "diagnóstico" filtra por diagnóstico inicial, post-RECA o ambos.
- Alinear el catálogo de "estado del caso" con §7.1.3 (activo, cerrado, derivado) y los tipos de alta con §7.5.4.
- EPIC-09 provee el motor de reportería transversal; EPIC-05 aporta la vista/reporte específico de cumplimiento para fiscalización.
