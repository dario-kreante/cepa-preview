# EPIC-09 — Reportería y Dashboard

**Módulo PRD:** §7.9 · §7.10
**Prioridad (MoSCoW):** P0 Must
**Reemplaza:** la generación manual de indicadores y reportes desde las 7 planillas Excel
**Perfiles operativos:** Coordinación · Administrativo · Auditor (NO Clínico — ver Decisiones v4 D1)

Tableros de control interactivos con visualización en tiempo real de indicadores de gestión y un conjunto de reportes descargables en formatos estándar. El dashboard mide la gestión **integral** del CEPA (multiprograma, no un solo programa — D5) y debe permitir filtrar por múltiples dimensiones temporales, profesionales, clínicas y demográficas. Sustenta los objetivos OU3 (estado completo de un caso <10 s), OI2 (reporte mensual de convenio <5 min) y OI1 (trazabilidad). Coordinación es el perfil principal de explotación; el perfil Administrativo dispone de ventanas de visualización por proceso; Auditor accede en solo lectura.

## Historias
- **CEPA-090** — Dashboard multiprograma con filtros (§7.9 · D5) — Coordinación · P0
- **CEPA-091** — Reportes operativos descargables (§7.9) — Coordinación · P0
- **CEPA-092** — Reporte de cumplimiento por convenio (§6.3 · §7.9) — Coordinación · P0
- **CEPA-093** — Reporte de carga laboral por profesional (§7.9) — Coordinación · P0
- **CEPA-094** — Reporte de licencias médicas acumuladas (§7.9) — Coordinación · P0
- **CEPA-095** — Métricas de adherencia y avance de tratamiento (§7.9 · D5 · D7) — Coordinación · P1
- **CEPA-096** — Ventanas de visualización por proceso (§7.10) — Administrativo · P1
- **CEPA-097** — Reporte de ODAS vencidas (D3) — Administrativo · P0

---

## [CEPA-090] Dashboard multiprograma con filtros

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.9
**Trazabilidad:** PRD §7.9 · §6.3 · Decisiones v4: D1, D5

### Historia
Como **coordinadora del CEPA**, quiero **un dashboard con indicadores de gestión en tiempo real que mida la operación integral del CEPA (todos los programas) y que pueda filtrar por múltiples dimensiones** para **tomar decisiones informadas sin esperar que alguien procese manualmente las planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora abre el dashboard
  - **Cuando** la vista carga
  - **Entonces** el sistema muestra indicadores agregados de **todos los programas** (atenciones, inasistencias, carga por profesional, cumplimiento de convenios) actualizados en tiempo real, sin requerir procesamiento manual previo.
- **CA-2**
  - **Dado** que la coordinadora aplica uno o varios filtros (temporal, profesional, especialidad, tipo de atención, programa, diagnóstico, tipo de alta, tramo etario, sexo, zona geográfica, modelo de tratamiento, tipo de ingreso, origen, tipo de convenio, duración)
  - **Cuando** confirma la selección
  - **Entonces** todos los indicadores y gráficos se recalculan según los filtros aplicados y muestran únicamente los datos del recorte seleccionado.
- **CA-3**
  - **Dado** que la coordinadora consulta el estado completo de la gestión sobre un volumen de datos en producción
  - **Cuando** carga o filtra el dashboard
  - **Entonces** el resultado se presenta en **menos de 10 segundos** (objetivo OU3).
- **CA-4**
  - **Dado** que un usuario con perfil Administrativo o Auditor accede al dashboard
  - **Cuando** la vista carga
  - **Entonces** ve los indicadores en solo lectura (sin configuración del dashboard ni acceso de edición de datos).

### Reglas de Negocio
- **RN-1:** El dashboard es **multiprograma** por defecto: agrega la gestión integral del CEPA; «programa» es una dimensión de filtro, no el alcance fijo de la vista (D5).
- **RN-2:** Dimensiones de filtro requeridas: temporal (diario/semanal/mensual/anual), profesional (médico/psicólogo/EISTA), especialidad, tipo de atención, duración (relevante para telemedicina), tipo de tratamiento, origen, tipo de convenio, programa, y (D5) diagnósticos, tipos de alta, tramos etarios, sexo, zona geográfica (región/comuna), modelo de tratamiento, tipo de ingreso.
- **RN-3:** Los filtros son combinables (AND); el dashboard mantiene coherencia entre todos los widgets ante un mismo recorte.
- **RN-4:** Los indicadores se calculan en tiempo real sobre la fuente única de verdad (no sobre exports estáticos).
- **RN-5:** Objetivo de rendimiento OU3 — el estado completo/recálculo se entrega en <10 s sobre volúmenes de producción; requiere paginación, indexación y/o agregaciones precalculadas.
- **RN-6:** RBAC — Coordinación tiene acceso total y configuración; Administrativo y Auditor acceden en solo lectura; el perfil Clínico no existe en el sistema (D1).
- **RN-7:** Cada métrica del dashboard debe pasar el QA de métricas (validación de resultado y de proceso, persona vs. programador — D5); no se publica un indicador sin validación.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-090-01 | Positivo | Datos de varios programas cargados | Abrir dashboard sin filtros | Múltiples programas | Indicadores agregados integrales en tiempo real | Alta |
| TC-090-02 | Positivo | Dashboard abierto | Aplicar filtros combinados (programa + tramo etario + sexo + temporal mensual) | Programa A, 18-29, F, mes actual | Todos los widgets se recalculan al recorte seleccionado | Alta |
| TC-090-03 | No funcional | Volumen de producción | Cargar/filtrar y medir tiempo de respuesta | ~3.000 registros | Resultado entregado en <10 s (OU3) | Alta |
| TC-090-04 | Borde | Filtro sin coincidencias | Aplicar combinación de filtros sin datos | Comuna sin casos | Estado vacío explícito, sin error ni cifras erróneas | Media |
| TC-090-05 | Permisos | Sesión con perfil Auditor | Acceder al dashboard e intentar configurar | Usuario auditor | Lectura permitida; configuración/edición denegada | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría (si aplica)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Tramos etarios y zona geográfica (región/comuna) dependen de campos obligatorios de calidad de datos (D6).
- Estrategia de rendimiento (vistas materializadas/agregaciones) a confirmar con Oracle institucional para cumplir OU3.

---

## [CEPA-091] Reportes operativos descargables

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.9
**Trazabilidad:** PRD §7.9 · Decisiones v4: D1

### Historia
Como **coordinadora del CEPA**, quiero **generar y descargar reportes operativos de citas, atenciones, inasistencias y anulaciones en formatos estándar** para **disponer de información accionable y compartible sin procesar manualmente las planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora selecciona el reporte operativo y define el período y los filtros
  - **Cuando** genera el reporte
  - **Entonces** el sistema produce las cifras de citas, atenciones, inasistencias y anulaciones del recorte solicitado.
- **CA-2**
  - **Dado** que un reporte fue generado
  - **Cuando** la coordinadora elige descargarlo
  - **Entonces** el sistema entrega el archivo en un formato estándar (p. ej. Excel/CSV y PDF) con los datos visibles en pantalla.
- **CA-3**
  - **Dado** que un usuario con perfil Auditor accede a los reportes operativos
  - **Cuando** los genera/descarga
  - **Entonces** puede hacerlo en solo lectura, sin alterar datos de origen.

### Reglas de Negocio
- **RN-1:** El reporte cubre cuatro métricas operativas: citas, atenciones, inasistencias y anulaciones, parametrizables por período y filtros.
- **RN-2:** Descargable en al menos un formato estándar tabular (Excel/CSV) y un formato de presentación (PDF).
- **RN-3:** Las cifras del archivo descargado deben coincidir exactamente con las mostradas en pantalla para el mismo recorte (consistencia export ↔ vista).
- **RN-4:** RBAC — Coordinación y Auditor pueden generar/descargar; Administrativo según asignación; ningún perfil edita datos de origen al exportar (D1).
- **RN-5:** La generación de reportes queda trazada en el log de auditoría (quién generó qué reporte y cuándo).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-091-01 | Positivo | Datos del período disponibles | Seleccionar reporte → período → generar | Mes actual | Cifras correctas de citas/atenciones/inasistencias/anulaciones | Alta |
| TC-091-02 | Positivo | Reporte generado | Descargar en Excel y en PDF | — | Archivos válidos con datos idénticos a la vista | Alta |
| TC-091-03 | Negativo | Sin período válido | Generar sin definir período | Período vacío | Error de validación; no genera reporte | Media |
| TC-091-04 | Borde | Período sin actividad | Generar reporte de período sin citas | Mes sin datos | Reporte con totales en cero, sin error | Media |
| TC-091-05 | Permisos | Sesión con perfil sin acceso a reportes | Intentar generar reporte | Usuario sin permiso | Acceso denegado | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar catálogo de estados de cita (realizada/inasistencia/anulación) con Coordinación para consistencia de conteos.

---

## [CEPA-092] Reporte de cumplimiento por convenio

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.9
**Trazabilidad:** PRD §6.3 · §7.9 · OI2 · Decisiones v4: D1

### Historia
Como **coordinadora del CEPA**, quiero **generar el reporte mensual de convenio con un clic, filtrando por período, profesional, tipo de atención y programa** para **cumplir los compromisos de información hacia las instituciones contraparte en minutos en vez de días**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora selecciona un convenio y un período mensual
  - **Cuando** hace clic en generar
  - **Entonces** el sistema produce el reporte de cumplimiento del convenio con los indicadores comprometidos para ese período.
- **CA-2**
  - **Dado** que la coordinadora quiere acotar el reporte
  - **Cuando** aplica filtros por profesional, tipo de atención y programa
  - **Entonces** el reporte se restringe al recorte seleccionado y permite su descarga en formato estándar.
- **CA-3**
  - **Dado** que se genera el reporte mensual de convenio sobre volúmenes de producción
  - **Cuando** la coordinadora lo solicita
  - **Entonces** el resultado se obtiene en **menos de 5 minutos** (objetivo OI2), frente a los 2-3 días manuales actuales.

### Reglas de Negocio
- **RN-1:** El reporte se genera con un solo clic una vez seleccionados convenio y período (mínima fricción operativa).
- **RN-2:** Filtros disponibles: período, profesional, tipo de atención y programa.
- **RN-3:** Objetivo de tiempo OI2 — generación en <5 min para el reporte mensual de convenio.
- **RN-4:** El reporte es descargable en formato estándar apto para entrega a la institución contraparte.
- **RN-5:** Tipos de convenio/derivación según valores reales (D4): DIEP, DIAT, PAPT a flujo AT, Reingreso FUMP, Reingreso SUSESO, Convenio U.Clínica, Proyecto, Particular, PAPT (sin «convenio SOCORRO»).
- **RN-6:** RBAC — Coordinación genera; Auditor accede en solo lectura para verificación de cumplimiento; el perfil Clínico no existe (D1).
- **RN-7:** La generación queda trazada en el log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-092-01 | Positivo | Convenio con datos del mes | Seleccionar convenio + mes → un clic generar | Convenio ISL, mes actual | Reporte de cumplimiento generado con indicadores del período | Alta |
| TC-092-02 | Positivo | Reporte generado | Filtrar por profesional + tipo de atención + programa y descargar | Prof. X, telemedicina, Programa A | Reporte acotado y descargable en formato estándar | Alta |
| TC-092-03 | No funcional | Volumen de producción | Generar reporte mensual y medir tiempo | Mes completo | Generado en <5 min (OI2) | Alta |
| TC-092-04 | Borde | Convenio sin actividad en el mes | Generar reporte | Convenio sin casos | Reporte válido con totales en cero | Media |
| TC-092-05 | Permisos | Sesión con perfil Administrativo sin asignación de convenios | Intentar generar reporte de convenio | Usuario sin permiso | Acceso denegado | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar con cada institución contraparte (p. ej. ISL) los indicadores exactos y el layout esperado del reporte mensual.

---

## [CEPA-093] Reporte de carga laboral por profesional

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.9
**Trazabilidad:** PRD §7.9 · §6.3 · Decisiones v4: D1

### Historia
Como **coordinadora del CEPA**, quiero **generar un reporte de carga laboral por profesional (médico, psicólogo, EISTA)** para **distribuir el trabajo de forma equilibrada y detectar sobrecarga sin revisar planillas manualmente**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora selecciona el reporte de carga laboral y un período
  - **Cuando** lo genera
  - **Entonces** el sistema muestra, por profesional, el volumen de casos/atenciones asignados en ese período.
- **CA-2**
  - **Dado** que la coordinadora quiere comparar
  - **Cuando** filtra por especialidad, tipo de atención o programa
  - **Entonces** el reporte recalcula la carga del recorte y permite descargarlo en formato estándar.
- **CA-3**
  - **Dado** que un usuario con perfil Auditor accede
  - **Cuando** consulta el reporte
  - **Entonces** lo ve en solo lectura.

### Reglas de Negocio
- **RN-1:** La carga se computa por profesional (médico tratante, psicólogo, EISTA) sobre casos/atenciones del período.
- **RN-2:** Filtros: temporal, especialidad, tipo de atención, programa.
- **RN-3:** El reporte es descargable en formato estándar.
- **RN-4:** El profesional es un dato de referencia, no un usuario con acceso (D1): la carga se atribuye al profesional asignado en el registro, no a una sesión de usuario.
- **RN-5:** RBAC — Coordinación genera; Auditor solo lectura.
- **RN-6:** La métrica de carga debe pasar el QA de métricas (D5).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-093-01 | Positivo | Casos asignados a varios profesionales | Generar reporte por período | Mes actual | Carga correcta por profesional | Alta |
| TC-093-02 | Positivo | Reporte generado | Filtrar por especialidad y descargar | Psicólogos | Reporte acotado y descargable | Media |
| TC-093-03 | Borde | Profesional sin casos en el período | Generar reporte | Prof. sin asignaciones | Profesional listado con carga cero | Media |
| TC-093-04 | Negativo | Sin período | Generar sin definir período | Período vacío | Error de validación | Media |
| TC-093-05 | Permisos | Sesión Auditor | Generar/descargar reporte | Usuario auditor | Solo lectura permitida | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría (si aplica)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir la unidad de carga (nº de casos activos vs. nº de atenciones vs. horas estimadas) con Coordinación.

---

## [CEPA-094] Reporte de licencias médicas acumuladas

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.9
**Trazabilidad:** PRD §7.9 · §7.7.3 · Decisiones v4: D1, D8

### Historia
Como **coordinadora del CEPA**, quiero **generar un reporte de licencias médicas acumuladas por paciente** para **monitorear los días de reposo totales y detectar casos críticos sin recalcular manualmente la planilla de licencias**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora genera el reporte de licencias acumuladas para un período
  - **Cuando** lo solicita
  - **Entonces** el sistema muestra, por paciente/folio, el total de días de licencia acumulados sumando todas sus licencias.
- **CA-2**
  - **Dado** que la coordinadora aplica filtros (período, región/comuna, tipo de licencia, tipo de reposo, programa)
  - **Cuando** confirma
  - **Entonces** el reporte recalcula sobre el recorte y permite descargarlo en formato estándar.
- **CA-3**
  - **Dado** que existen licencias **extra-sistema** registradas (D7)
  - **Cuando** se genera el reporte
  - **Entonces** se incluyen en el acumulado si así se configuró, distinguidas como tales.

### Reglas de Negocio
- **RN-1:** El total acumulado por paciente suma todas las licencias del folio (consistente con el cálculo automático de EPIC-07/§7.7.3).
- **RN-2:** Filtros: período, zona geográfica (región/comuna), tipo de licencia (1/5/6), tipo de reposo (total/parcial), programa.
- **RN-3:** Datos de licencia conforme a D8 (días de reposo, inicio/fin de reposo, fecha de emisión, tipo de licencia, indicación y diagnóstico, tipo de reposo).
- **RN-4:** Las licencias extra-sistema (D7) pueden incluirse en el acumulado, marcadas como origen externo.
- **RN-5:** Descargable en formato estándar.
- **RN-6:** RBAC — Coordinación genera; Auditor solo lectura; el cálculo acumulado debe pasar el QA de métricas (D5).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-094-01 | Positivo | Paciente con 4 licencias | Generar reporte | Folio con 4 LM | Total de días acumulados correcto por paciente | Alta |
| TC-094-02 | Borde | Paciente con licencia extra-sistema | Generar reporte incluyendo extra-sistema | 1 LM externa + 2 internas | Acumulado correcto, externa marcada como tal | Media |
| TC-094-03 | Positivo | Datos disponibles | Filtrar por región y tipo de reposo, descargar | Región Maule, reposo total | Reporte acotado y descargable | Media |
| TC-094-04 | Negativo | Sin período | Generar sin período | Período vacío | Error de validación | Media |
| TC-094-05 | Permisos | Sesión Auditor | Generar/descargar | Usuario auditor | Solo lectura permitida | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría (si aplica)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar si las licencias extra-sistema (D7) se incluyen por defecto o sólo bajo selección explícita.

---

## [CEPA-095] Métricas de adherencia y avance de tratamiento

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P1 Should
**Módulo PRD:** 7.9
**Trazabilidad:** PRD §7.9 (Reporte de seguimiento de tratamientos, P1) · Decisiones v4: D5, D7

### Historia
Como **coordinadora del CEPA**, quiero **métricas de adherencia y de avance del tratamiento, junto con estadísticas de fármacos** para **evaluar la efectividad del seguimiento clínico-administrativo y anticipar altas o ajustes de sesiones**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que la coordinadora consulta la métrica de adherencia
  - **Cuando** selecciona un recorte (paciente, programa, profesional o período)
  - **Entonces** el sistema muestra el **% de adherencia = nº de citas realizadas / nº de citas agendadas** del recorte.
- **CA-2**
  - **Dado** que la coordinadora consulta el avance del tratamiento
  - **Cuando** selecciona un caso o plan de tratamiento
  - **Entonces** el sistema muestra la **etapa del tratamiento** (p. ej. 10/15/21 sesiones), las **sesiones restantes para posible alta**, el % de avance por plan y los **aumentos de sesiones entregados por ISL**.
- **CA-3**
  - **Dado** que la coordinadora consulta estadísticas de fármacos
  - **Cuando** filtra por tratamiento, programa o profesional
  - **Entonces** el sistema muestra las estadísticas de fármacos utilizados en ese recorte (D7).
- **CA-4**
  - **Dado** que una métrica se publica en el dashboard/reporte
  - **Cuando** pasa el control de calidad
  - **Entonces** cuenta con validación de **resultado** y de **proceso** (persona vs. programador) y un responsable de QA de métricas asignado (D5).

### Reglas de Negocio
- **RN-1:** % adherencia = citas realizadas / citas agendadas (D5); el denominador excluye citas no aplicables según catálogo de estados acordado.
- **RN-2:** Avance del tratamiento mide etapa (sesiones realizadas vs. plan), sesiones restantes para posible alta y % por plan; debe contemplar los aumentos de sesiones entregados por ISL (D5).
- **RN-3:** Estadísticas de fármacos se computan por tratamiento, programa y profesional, considerando el esquema farmacológico y fármacos extra-sistema (D7).
- **RN-4:** QA de métricas obligatorio: cada métrica requiere validación de resultado y de proceso, con responsable definido (D5); no se publica sin validación.
- **RN-5:** RBAC — Coordinación explota estas métricas; Auditor solo lectura; el perfil Clínico no existe (D1).
- **RN-6:** P1 (fast-follow): el caso de uso principal del sistema funciona sin estas métricas; se priorizan tras los módulos P0.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-095-01 | Positivo | Paciente con 8 realizadas de 10 agendadas | Consultar adherencia del paciente | 8/10 | % adherencia = 80% | Alta |
| TC-095-02 | Positivo | Plan de 15 sesiones, 10 realizadas, +3 ISL | Consultar avance del tratamiento | 10/15 (+3 ISL) | Etapa, sesiones restantes y aumentos ISL correctos | Alta |
| TC-095-03 | Borde | Paciente con 0 citas agendadas | Calcular adherencia | 0 agendadas | Sin división por cero; estado "no aplica/sin datos" | Media |
| TC-095-04 | Positivo | Fármacos registrados | Estadísticas de fármacos por programa | Programa A | Estadísticas correctas por programa, incl. extra-sistema | Media |
| TC-095-05 | Permisos | Sesión Auditor | Consultar métricas | Usuario auditor | Solo lectura permitida | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría (si aplica)
- [ ] QA de métricas: validación de resultado y de proceso firmada por responsable (D5)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir responsable de QA de métricas (D5) y catálogo de estados de cita que cuentan como "realizada" para adherencia.
- Confirmar planes de tratamiento de referencia (10/15/21 sesiones) y la regla de aumentos ISL con Coordinación.

---

## [CEPA-096] Ventanas de visualización por proceso

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P1 Should
**Módulo PRD:** 7.10
**Trazabilidad:** PRD §7.10 · Decisiones v4: D1

### Historia
Como **administrativo del CEPA**, quiero **vistas consolidadas y personalizadas por proceso (licencias, fármacos, auditoría, reintegro, controles)** para **acceder a la información relevante de cada proceso de forma accionable sin abrir múltiples módulos ni planillas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que el administrativo abre la ventana de un proceso (p. ej. gestión de licencias)
  - **Cuando** la vista carga
  - **Entonces** el sistema muestra la información consolidada de ese proceso con sus campos relevantes y acciones disponibles.
- **CA-2**
  - **Dado** que el administrativo está en una ventana de proceso
  - **Cuando** aplica filtros u ordena la información
  - **Entonces** la vista se actualiza mostrando solo los registros del recorte y permite acceder al detalle de cada caso.
- **CA-3**
  - **Dado** que existen las cinco vistas de proceso (licencias, fármacos, auditoría, reintegro, controles)
  - **Cuando** el administrativo navega entre ellas
  - **Entonces** cada una presenta su información específica de forma accionable.
- **CA-4**
  - **Dado** que el usuario es Auditor
  - **Cuando** abre la vista de gestión de auditoría
  - **Entonces** accede en solo lectura sin edición de datos clínicos.

### Reglas de Negocio
- **RN-1:** Vistas requeridas: gestión de licencias médicas, gestión de fármacos, gestión de auditoría, gestión de reintegro y gestión de controles médicos (§7.10).
- **RN-2:** Cada vista consolida datos de su módulo de origen (EPIC-02/04/05/06/07) como información accionable (filtrar, ordenar, abrir detalle, ejecutar acciones del rol).
- **RN-3:** Las vistas presentan datos en tiempo real desde la fuente única de verdad; no son exports estáticos.
- **RN-4:** RBAC — el Administrativo opera las vistas de sus módulos asignados; Auditor accede en solo lectura (especialmente auditoría); Coordinación con acceso total; el perfil Clínico no existe (D1).
- **RN-5:** El estado completo de un caso/proceso debe ser accesible rápidamente (alineado con OU3, <10 s).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-096-01 | Positivo | Datos en módulo de licencias | Abrir vista de gestión de licencias | — | Información consolidada y accionable del proceso | Alta |
| TC-096-02 | Positivo | Vista de proceso abierta | Filtrar y abrir el detalle de un caso | Filtro por estado | Vista filtrada; detalle accesible | Media |
| TC-096-03 | Positivo | Cinco vistas disponibles | Navegar entre licencias/fármacos/auditoría/reintegro/controles | — | Cada vista muestra su información específica | Media |
| TC-096-04 | Borde | Proceso sin registros | Abrir vista de un proceso vacío | Sin datos | Estado vacío explícito, sin error | Media |
| TC-096-05 | Permisos | Sesión Auditor en vista de auditoría | Intentar editar datos clínicos | Usuario auditor | Solo lectura; edición denegada | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger (si aplica)
- [ ] Operaciones registradas en log de auditoría (si aplica)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar con cada equipo administrativo las columnas y acciones por defecto de cada vista de proceso.

---

## [CEPA-097] Reporte de ODAS vencidas

**Épica:** EPIC-09 — Reportería y Dashboard
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.9
**Trazabilidad:** PRD §7.9 · Decisiones v4: D3

### Historia
Como **administrativo del CEPA**, quiero **un reporte de ODAS (Órdenes de Primera Atención) vencidas** para **identificar y gestionar las órdenes que superaron su fecha de vigencia, complementando el registro y la alerta de ODAS**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que el administrativo genera el reporte de ODAS vencidas
  - **Cuando** lo solicita
  - **Entonces** el sistema lista todas las ODAS cuya fecha de vencimiento ya pasó respecto de la fecha actual, con su folio/paciente, fecha de registro y fecha de vencimiento.
- **CA-2**
  - **Dado** que el administrativo aplica filtros (período, programa, región/comuna)
  - **Cuando** confirma
  - **Entonces** el reporte se acota al recorte y permite descargarlo en formato estándar.
- **CA-3**
  - **Dado** que una ODA aún no ha vencido
  - **Cuando** se genera el reporte de vencidas
  - **Entonces** dicha ODA no aparece en el listado (sí estaría cubierta por la alerta de ODAS por vencer, fuera de esta historia).

### Reglas de Negocio
- **RN-1:** Una ODA está «vencida» cuando su fecha de vencimiento es anterior a la fecha actual del sistema (D3).
- **RN-2:** Las ODAS se ingresan manualmente y poseen fecha de vencimiento (D3); el reporte complementa el registro de ODA y la alerta de ODAS por vencer (EPIC-01/EPIC-10).
- **RN-3:** Filtros: período, programa, zona geográfica (región/comuna).
- **RN-4:** Descargable en formato estándar.
- **RN-5:** RBAC — Administrativo y Coordinación generan; Auditor solo lectura; el perfil Clínico no existe (D1).
- **RN-6:** La generación del reporte queda trazada en el log de auditoría.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-097-01 | Positivo | Existen ODAS vencidas y vigentes | Generar reporte de ODAS vencidas | Fecha actual 2026-06-03 | Solo las ODAS con vencimiento anterior a hoy | Alta |
| TC-097-02 | Borde | ODA que vence exactamente hoy | Generar reporte | Vence = hoy | ODA no listada como vencida (regla < hoy) | Media |
| TC-097-03 | Positivo | ODAS vencidas en varias comunas | Filtrar por región y descargar | Región Maule | Reporte acotado y descargable | Media |
| TC-097-04 | Borde | Sin ODAS vencidas | Generar reporte | Todas vigentes | Listado vacío explícito, sin error | Media |
| TC-097-05 | Permisos | Sesión Auditor | Generar/descargar reporte | Usuario auditor | Solo lectura permitida | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar la definición exacta de vencimiento (estricto `< hoy` vs. `<= hoy`) con Coordinación.
- El registro de ODA y la alerta de ODAS por vencer se especifican en EPIC-01 (registro) y EPIC-10 (alertas).
