# EPIC-04 — Seguimiento de Reintegro

**Módulo PRD:** §7.4 — Módulo de Seguimiento de Reintegro
**Prioridad (MoSCoW):** P0 Must
**Reemplaza:** hoja Excel «Seguimiento Reintegro» (24 columnas)
**Objetivo:** gestionar el proceso de reintegro laboral del usuario post-tratamiento, desde el registro del caso y su Resolución de Calificación (RECA) con medidas correctivas, hasta el reintegro efectivo (parcial o total), el término de la Licencia Médica (LM), la remisión al ISL y el cierre del caso con alta médica/psicológica.

**Perfiles operativos (RBAC):** Coordinación · Administrativo · Auditor. **El perfil Clínico NO accede al sistema** (Decisiones v4 · D1): el clínico registra en SALUTEM/SAM. La gestión del reintegro la realiza un funcionario **Administrativo**; **Coordinación** tiene lectura total y **Auditor** lectura sin edición.

## Glosario de la épica
| Término | Definición |
|---------|------------|
| **RECA** | Resolución de Calificación: documento de la mutualidad/ISL que califica el origen (enfermedad profesional / accidente del trabajo) y los riesgos del caso. |
| **ISL** | Instituto de Seguridad Laboral. Organismo al que se remiten casos y medidas. |
| **LM** | Licencia Médica. Su término marca la fecha de reintegro. |
| **Reintegro parcial** | Reincorporación laboral con jornada/funciones reducidas o adaptadas, sin término total de la LM. |
| **Reintegro total** | Reincorporación laboral completa a las funciones habituales, con término de la LM. |
| **Medidas correctivas** | Acciones que el empleador debe implementar (y verificar) para mitigar los riesgos calificados en la RECA. |

## Historias de la épica
| ID | Título | Perfil | PRD |
|----|--------|--------|-----|
| CEPA-040 | Datos del caso de reintegro | Administrativo | §7.4.1 |
| CEPA-041 | Proceso RECA y medidas correctivas | Administrativo | §7.4.2 |
| CEPA-042 | Reintegro y cierre del caso | Administrativo | §7.4.3 |

---

## [CEPA-040] Datos del caso de reintegro

**Épica:** EPIC-04 — Seguimiento de Reintegro
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.4.1
**Trazabilidad:** PRD §7.4.1 · Decisiones v4: D1, D4, D5, D6

**Campos:**
- Folio (vinculado al módulo de Ingresos; secuencial automático con opción manual para reingresos — D2)
- Tipo de derivación (valores reales D4: DIEP · DIAT · PAPT a flujo AT · Reingreso FUMP · Reingreso SUSESO · Convenio U.Clínica · Proyecto · Particular · PAPT)
- Fecha del caso de reintegro
- Nombre completo del usuario
- RUT (con validación de dígito verificador)
- Región
- **Datos sociodemográficos repetidos** (v4 · D5/D6): sexo, edad/tramo etario, zona geográfica (región y comuna)
- **Zona geográfica** del usuario (región, comuna)
- **Rubro / actividad económica del empleador** (v4)

### Historia
Como **Administrativo**, quiero **registrar los datos del caso de reintegro de un usuario (folio, tipo de derivación, fecha, identificación, región, zona geográfica y rubro del empleador)** para **iniciar el seguimiento del reintegro laboral vinculado a su folio sin transcribir datos a la planilla Excel**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un Administrativo abre el formulario de nuevo caso de reintegro
  - **Cuando** ingresa un RUT válido ya existente en el sistema
  - **Entonces** el sistema pre-llena nombre, región y datos sociodemográficos desde el folio del usuario y permite confirmar o actualizar.
- **CA-2**
  - **Dado** que un Administrativo completa todos los campos obligatorios del caso
  - **Cuando** guarda el registro
  - **Entonces** el caso queda vinculado al folio del usuario y es visible desde el módulo de Ingresos y desde la vista de gestión de reintegro.
- **CA-3**
  - **Dado** que un Administrativo ingresa un RUT con dígito verificador inválido
  - **Cuando** hace clic en guardar
  - **Entonces** el sistema muestra un error específico de RUT y conserva el resto de los datos ingresados.
- **CA-4**
  - **Dado** que un Administrativo selecciona el tipo de derivación
  - **Cuando** abre la lista de valores
  - **Entonces** solo se ofrecen los valores reales de D4 y "convenio SOCORRO" no aparece.

### Reglas de Negocio
- **RN-1:** El folio es la clave de vinculación con Ingresos; un caso de reintegro siempre pertenece a un folio existente (o reingreso que mantiene folio anterior — D2).
- **RN-2:** RUT obligatorio y validado por dígito verificador; folio, tipo de derivación, fecha, nombre y región son obligatorios (D6 — calidad de datos).
- **RN-3:** Tipo de derivación restringido al catálogo D4 (sin "convenio SOCORRO").
- **RN-4:** Sexo, edad/tramo etario, zona geográfica (región, comuna) son obligatorios para datos limpios, fidedignos y comparables (D5/D6) y alimentan los filtros del dashboard.
- **RN-5:** Toda operación de creación/edición se registra en el log de auditoría (quién, qué, cuándo).
- **RN-6:** Solo Administrativo y Coordinación pueden crear/editar; Auditor solo lectura.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-040-01 | Positivo | Usuario con folio existente | Abrir formulario, ingresar RUT existente, confirmar datos, guardar | RUT 12.345.678-5 | Datos pre-llenados; caso creado y vinculado al folio | Alta |
| TC-040-02 | Positivo | Tipo de derivación = Reingreso FUMP | Completar caso con valor D4 y guardar | Reingreso FUMP | Caso guardado con tipo de derivación válido | Alta |
| TC-040-03 | Negativo | Formulario abierto | Ingresar RUT con DV incorrecto y guardar | 12.345.678-0 | Error de RUT; demás datos conservados | Alta |
| TC-040-04 | Negativo | Formulario abierto | Omitir sexo/zona geográfica y guardar | Campos obligatorios vacíos | Bloqueo con mensaje de campos requeridos | Alta |
| TC-040-05 | Borde | Reingreso del usuario tras alta | Ingreso manual de folio previo del usuario | Folio histórico | Caso vinculado al folio anterior (D2) sin duplicar usuario | Media |
| TC-040-06 | Permisos | Sesión con perfil Auditor | Intentar crear/editar un caso de reintegro | — | Acción denegada; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar catálogo de "rubro / actividad económica del empleador" (¿lista cerrada CIIU o texto?).
- Reingresos vs. nuevas denuncias bajo el mismo RUT: diferenciación por número de siniestro (D2) — definir si el caso de reintegro hereda siniestro de Ingresos.

---

## [CEPA-041] Proceso RECA y medidas correctivas

**Épica:** EPIC-04 — Seguimiento de Reintegro
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.4.2
**Trazabilidad:** PRD §7.4.2 · Decisiones v4: D1, D6

**Campos:**
- Fecha de RECA
- Tipo de RECA
- Nº de RECA
- Solicitud de medidas correctivas (sí/no + detalle)
- Verificación de medidas correctivas (sí/no + detalle)
- Medidas correctivas (descripción)
- Fecha de medidas correctivas
- Fecha de verificación de medidas
- Riesgos calificados (en la RECA)
- Razón social del empleador

### Historia
Como **Administrativo**, quiero **registrar la RECA del caso (fecha, tipo, número), los riesgos calificados y el ciclo de medidas correctivas con sus fechas de solicitud, implementación y verificación** para **controlar el cumplimiento de las medidas exigidas por la mutualidad/ISL sin perder seguimiento de los plazos del empleador**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un caso de reintegro existente sin RECA registrada
  - **Cuando** el Administrativo ingresa fecha, tipo y Nº de RECA y guarda
  - **Entonces** la RECA queda asociada al caso y visible en la vista de gestión de reintegro y de auditoría.
- **CA-2**
  - **Dado** que la RECA marca solicitud de medidas correctivas = Sí
  - **Cuando** el Administrativo intenta guardar sin describir las medidas ni su fecha
  - **Entonces** el sistema exige el detalle y la fecha de las medidas antes de guardar.
- **CA-3**
  - **Dado** una medida correctiva con fecha de medidas registrada
  - **Cuando** se registra la verificación de la medida
  - **Entonces** la fecha de verificación debe ser igual o posterior a la fecha de la medida; en caso contrario el sistema rechaza el dato.
- **CA-4**
  - **Dado** un caso con riesgos calificados registrados
  - **Cuando** el Auditor consulta el caso
  - **Entonces** visualiza RECA, riesgos calificados y estado de medidas en modo solo lectura.

### Reglas de Negocio
- **RN-1:** Nº de RECA único por caso; fecha y tipo de RECA obligatorios cuando se registra una RECA.
- **RN-2:** Si solicitud de medidas correctivas = Sí, son obligatorios el detalle de las medidas y la fecha de medidas.
- **RN-3:** Fecha de verificación ≥ fecha de medidas ≥ fecha de RECA (coherencia temporal).
- **RN-4:** Verificación = Sí requiere fecha de verificación registrada.
- **RN-5:** Razón social del empleador obligatoria; debe ser consistente con el rubro/actividad económica de CEPA-040.
- **RN-6:** Toda operación se registra en el log de auditoría. Solo Administrativo/Coordinación editan; Auditor solo lectura.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-041-01 | Positivo | Caso de reintegro sin RECA | Ingresar fecha, tipo y Nº de RECA, riesgos y razón social; guardar | RECA Nº 2026-0042 | RECA asociada al caso y visible en reintegro/auditoría | Alta |
| TC-041-02 | Positivo | RECA con medidas solicitadas | Registrar medida, fecha de medida y luego verificación con fecha posterior | Medida 10/03, verif. 25/03 | Ciclo de medida completo y verificado | Alta |
| TC-041-03 | Negativo | Solicitud de medidas = Sí | Guardar sin detalle ni fecha de medidas | Detalle vacío | Bloqueo: detalle y fecha de medidas obligatorios | Alta |
| TC-041-04 | Negativo | Medida con fecha 10/03 | Registrar verificación con fecha 05/03 | Verif. 05/03 | Rechazo por incoherencia temporal (RN-3) | Alta |
| TC-041-05 | Borde | Caso con RECA ya registrada | Intentar ingresar segundo Nº de RECA duplicado | Nº repetido | Rechazo por unicidad de Nº de RECA | Media |
| TC-041-06 | Permisos | Sesión Auditor | Intentar editar medidas correctivas | — | Acción denegada; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Confirmar catálogo de "tipo de RECA" y de "riesgos calificados" (lista cerrada vs. texto libre).
- Evaluar si se requiere alerta automática de medidas correctivas próximas a vencer (alinear con §7.11).

---

## [CEPA-042] Reintegro y cierre del caso

**Épica:** EPIC-04 — Seguimiento de Reintegro
**Perfil:** Administrativo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 7.4.3
**Trazabilidad:** PRD §7.4.3 · Decisiones v4: D1, D11

**Campos:**
- Estado del reintegro (pendiente · parcial · total)
- Fecha de reintegro (término de LM)
- Remitido a ISL (sí/no)
- Alta médica (sí/no + fecha)
- Alta psicológica (sí/no + fecha)
- Tipo de alta
- Observaciones (texto libre)

### Historia
Como **Administrativo**, quiero **registrar el estado y la fecha de reintegro (término de LM), la remisión al ISL, las altas médica/psicológica y el tipo de alta** para **cerrar el caso de reintegro con trazabilidad completa y alimentar los indicadores de reintegro parcial/total del dashboard**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un caso de reintegro con RECA y medidas verificadas
  - **Cuando** el Administrativo marca estado = Total e ingresa la fecha de reintegro
  - **Entonces** el sistema registra el término de la LM y refleja "reintegro total" en la vista de reintegro y en auditoría (§7.5.3).
- **CA-2**
  - **Dado** un caso con estado = Parcial
  - **Cuando** se guarda sin fecha de reintegro
  - **Entonces** el sistema permite guardar (reintegro parcial sin término total de LM) pero mantiene el caso abierto.
- **CA-3**
  - **Dado** un caso con reintegro total
  - **Cuando** el Administrativo registra alta médica y alta psicológica con tipo de alta
  - **Entonces** el caso queda en estado cerrado y la fecha de reintegro no puede ser anterior a la fecha de RECA.
- **CA-4**
  - **Dado** un caso marcado como remitido a ISL = Sí
  - **Cuando** el Auditor consulta el cierre del caso
  - **Entonces** visualiza estado de reintegro, fechas y altas en modo solo lectura.

### Reglas de Negocio
- **RN-1:** Estado de reintegro ∈ {pendiente, parcial, total}. "Total" exige fecha de reintegro (término de LM).
- **RN-2:** Fecha de reintegro ≥ fecha de RECA (CEPA-041) y ≥ fecha del caso (CEPA-040).
- **RN-3:** Reintegro parcial puede coexistir con LM vigente; reintegro total marca término de LM.
- **RN-4:** El cierre del caso requiere al menos alta médica o alta psicológica registrada con tipo de alta; tipo de alta obligatorio al cerrar (D11 — tipificación de altas; confirmar si una sola fecha de alta).
- **RN-5:** "Remitido a ISL" es sí/no; si Sí, queda disponible para el reporte de auditoría/contraparte.
- **RN-6:** Toda operación se registra en el log de auditoría. Solo Administrativo/Coordinación editan; Auditor solo lectura.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-042-01 | Positivo | Caso con RECA y medidas verificadas | Marcar estado Total, ingresar fecha de reintegro, altas y tipo de alta; guardar | Fecha 30/05, alta terapéutica | Reintegro total registrado; caso cerrado; reflejado en auditoría | Alta |
| TC-042-02 | Positivo | Caso en evaluación de reintegro | Marcar estado Parcial sin fecha de reintegro; guardar | Estado Parcial | Guardado; caso permanece abierto con LM vigente | Alta |
| TC-042-03 | Negativo | Estado = Total | Guardar sin fecha de reintegro | Fecha vacía | Bloqueo: fecha de reintegro obligatoria para total (RN-1) | Alta |
| TC-042-04 | Negativo | RECA con fecha 01/04 | Ingresar fecha de reintegro 15/03 | Reintegro 15/03 | Rechazo por incoherencia temporal (RN-2) | Alta |
| TC-042-05 | Borde | Caso con reintegro total y sin altas | Intentar cerrar sin alta ni tipo de alta | — | Bloqueo: requiere alta y tipo de alta para cerrar (RN-4) | Media |
| TC-042-06 | Permisos | Sesión Auditor | Intentar modificar estado de reintegro o altas | — | Acción denegada; solo lectura | Alta |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger
- [ ] Operaciones registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- D11: confirmar con Coordinación si el cierre usa una sola fecha de alta (última atención) independiente del tipo, o fechas separadas para alta médica y psicológica.
- Validar catálogo de "tipo de alta" (alta terapéutica, médica, psicológica, abandono, derivación — alinear con §7.1.3).
- Confirmar si "reintegro total" debe disparar automáticamente el cierre de la LM asociada en el módulo de Licencias Médicas (§7.7).
