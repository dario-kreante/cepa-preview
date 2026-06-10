# EPIC-12 — API de Integración

> Épica del **Módulo §8 — API de Integración** del PRD Sistema CEPA.
> Expone una API REST documentada para la integración escalable con sistemas externos
> de fichas clínicas electrónicas (SAM/SALUTEM), IMED y otros sistemas institucionales.
> **Prioridad de la épica:** P0 Must.
> **Objetivo institucional asociado:** OI3 — *100% de endpoints documentados y con tests*.

**Trazabilidad:** PRD §8 (§8.1 principios, §8.2 recursos, §8.3 integraciones) · Decisiones v4: D12.

**Glosario relevante**
- **IMED:** plataforma chilena de licencias médicas y recetas electrónicas.
- **SAM / SALUTEM:** sistemas de fichas clínicas electrónicas con que opera CEPA. El equipo clínico registra la información clínica directamente en ellos (Decisiones v4 D1). **El aplicativo CEPA no escribe sobre SALUTEM** (D12).
- **JWT:** JSON Web Token, mecanismo de autenticación basado en tokens firmados.
- **FastAPI:** framework web de Python para construir APIs REST; genera la especificación OpenAPI/Swagger de forma automática a partir de las anotaciones de tipos y los modelos Pydantic.
- **OpenAPI / Swagger:** estándar de especificación y documentación automática de APIs REST (generado automáticamente por FastAPI).

**Historias de la épica**
| ID | Título | Perfil | Prioridad |
|----|--------|--------|-----------|
| CEPA-120 | API REST versionada con auth, Swagger y rate limiting | Sistema / Desarrollo | P0 Must |
| CEPA-121 | Recursos clínicos bidireccionales | Sistema | P0 Must |
| CEPA-122 | Integración IMED | Sistema | P2 Could |

---

## [CEPA-120] API REST versionada con auth, Swagger y rate limiting

**Épica:** EPIC-12 — API de Integración
**Perfil:** Sistema / Desarrollo
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 8.1
**Trazabilidad:** PRD §8.1 (principios de diseño) · OI3 (100% endpoints documentados y con tests)

### Historia
Como **sistema integrador / desarrollador integrador**, quiero **consumir una API REST versionada (v1, v2), autenticada por tokens JWT, documentada automáticamente con OpenAPI/Swagger y protegida con rate limiting** para **integrar sistemas externos de forma estándar, segura y trazable sin acoplarme a versiones futuras del contrato**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un cliente externo con un token JWT válido y vigente
  - **Cuando** invoca un endpoint bajo el prefijo `/api/v1/...` enviando y esperando JSON
  - **Entonces** la API responde con código HTTP estándar (200/201) y cuerpo JSON conforme al contrato.
- **CA-2**
  - **Dado** un cliente sin token o con un token JWT inválido/expirado
  - **Cuando** invoca cualquier endpoint protegido
  - **Entonces** la API responde `401 Unauthorized` con cuerpo JSON de error, sin exponer datos del recurso.
- **CA-3**
  - **Dado** que la API expone documentación automática
  - **Cuando** un desarrollador accede a la ruta de Swagger UI / OpenAPI
  - **Entonces** se listan el 100% de los endpoints con sus esquemas de request/response, códigos de error y requisitos de autenticación.
- **CA-4**
  - **Dado** un cliente que supera el límite de solicitudes configurado por ventana de tiempo
  - **Cuando** envía una solicitud adicional dentro de la misma ventana
  - **Entonces** la API responde `429 Too Many Requests` indicando el tiempo de reintento.
- **CA-5**
  - **Dado** que existe la versión `v1` publicada
  - **Cuando** se publica `v2` con cambios incompatibles
  - **Entonces** `v1` sigue operativa bajo su prefijo y los clientes existentes no se rompen.

### Reglas de Negocio
- **RN-1:** Toda ruta pública de integración se sirve bajo un prefijo de versión explícito (`/api/v1`, `/api/v2`); no se publican endpoints sin versión.
- **RN-2:** Todos los endpoints de integración exigen autenticación JWT salvo los de salud/documentación; el token debe estar firmado, vigente y no expirado.
- **RN-3:** Request y response usan formato JSON; los errores devuelven códigos HTTP estándar (400, 401, 403, 404, 409, 422, 429, 500) con cuerpo JSON uniforme.
- **RN-4:** El rate limiting/throttling se aplica por cliente/token con una cuota por ventana de tiempo configurable; al excederla se responde `429`.
- **RN-5:** La especificación OpenAPI/Swagger se genera automáticamente desde el código y debe cubrir el 100% de los endpoints (criterio OI3); un endpoint sin documentar no cumple la DoD.
- **RN-6:** Toda operación de integración que cree o modifique datos queda registrada en el log de auditoría (quién/qué/cuándo), consistente con el RBAC del sistema.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-120-01 | Positivo | Token JWT válido | GET a un endpoint `/api/v1` con header `Authorization: Bearer <jwt>` | JWT vigente | `200 OK`, cuerpo JSON conforme al contrato | Alta |
| TC-120-02 | Negativo | Sin credenciales | GET a endpoint protegido sin header de autorización | — | `401 Unauthorized`, JSON de error, sin datos del recurso | Alta |
| TC-120-03 | Negativo | Token expirado | GET con `Authorization` portando un JWT expirado | JWT vencido | `401 Unauthorized` | Alta |
| TC-120-04 | No funcional (rate limit) | Cuota = N req/ventana | Enviar N+1 solicitudes en la misma ventana | N+1 requests | Las primeras N → `2xx`; la N+1 → `429 Too Many Requests` con reintento | Alta |
| TC-120-05 | No funcional (contrato OpenAPI) | API desplegada | Descargar el documento OpenAPI y validar que todos los endpoints expuestos figuran con esquemas | Spec OpenAPI | 100% de endpoints documentados; spec válida | Alta |
| TC-120-06 | Borde | `v1` y `v2` publicadas | Invocar el mismo recurso lógico en `/api/v1` y `/api/v2` | Dos prefijos | Ambas responden según su contrato; `v1` no se rompe por cambios de `v2` | Media |

### Definición de Hecho (DoD)
- [ ] API versionada (`/api/v1`) implementada y desplegada en QA
- [ ] Todos los CA verificados
- [ ] Autenticación JWT y rate limiting activos y testeados
- [ ] Tests unitarios + integración en verde
- [ ] 100% de endpoints documentados en OpenAPI/Swagger (OI3)
- [ ] Operaciones de escritura registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA (y validación técnica de Mario, Director de TI UTalca — D13)

### Notas / Preguntas abiertas
- Cumplimiento de seguridad/cifrado e integraciones supervisado por la contraparte técnica de TI UTalca (D13).
- Políticas adicionales de cifrado/retención/anonimización de datos sensibles por confirmar (PA3).

---

## [CEPA-121] Recursos clínicos bidireccionales

**Épica:** EPIC-12 — API de Integración
**Perfil:** Sistema
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** 8.2 / 8.3
**Trazabilidad:** PRD §8.2 (recursos) · §8.3 (integración con SAM/SALUTEM) · Decisiones v4: D12

### Historia
Como **sistema integrador**, quiero **exponer los recursos clínicos del CEPA (Pacientes, Ingresos, Fichas clínicas, Licencias) con intercambio bidireccional de datos con sistemas externos de fichas clínicas** para **enviar y recibir información clínica de forma sincronizada y consolidada sin duplicar registros**.

> **Nota de alcance (§8.2):** dentro de esta historia P0 se implementan **Pacientes, Ingresos, Fichas clínicas y Licencias**. Los recursos **Fármacos** y **Controles** son **P1** y **Reportes** es **P2**; se diseñan como extensión del mismo contrato pero quedan fuera del alcance P0.

### Criterios de Aceptación (Gherkin)
- **CA-1** (Pacientes)
  - **Dado** un cliente externo autenticado
  - **Cuando** solicita un paciente buscando por RUT, nombre o folio
  - **Entonces** la API devuelve los datos del paciente, o `404` si no existe, y permite operaciones CRUD según permisos.
- **CA-2** (Ingresos)
  - **Dado** un ingreso existente
  - **Cuando** el cliente consulta o actualiza su **estado**
  - **Entonces** la API refleja el estado actual del ingreso y persiste la actualización con trazabilidad.
- **CA-3** (Fichas clínicas — bidireccional)
  - **Dado** un sistema externo de fichas clínicas integrado
  - **Cuando** envía datos clínicos (push) o solicita datos clínicos (pull) del CEPA
  - **Entonces** la API procesa ambos sentidos del intercambio (recibir y entregar), confirmando recepción con código HTTP estándar.
- **CA-4** (Licencias)
  - **Dado** un paciente con licencias registradas
  - **Cuando** el cliente consulta su recurso de licencias
  - **Entonces** la API devuelve el **historial de licencias** y el **total de días acumulados** del folio.
- **CA-5** (No escribir sobre SALUTEM — D12)
  - **Dado** el intercambio bidireccional con la ficha clínica
  - **Cuando** el CEPA procesa datos clínicos provenientes de SAM/SALUTEM
  - **Entonces** el aplicativo **no realiza operaciones de escritura sobre SALUTEM**: solo recibe/consulta, y la persistencia ocurre en el dominio CEPA.

### Reglas de Negocio
- **RN-1:** La integración con la ficha clínica es **bidireccional** (push/pull), **no unidireccional** (D12).
- **RN-2:** El aplicativo CEPA **no escribe sobre SALUTEM**; la bidireccionalidad significa recibir datos clínicos y exponer/entregar datos del CEPA, sin mutar el sistema de origen (D12).
- **RN-3:** El recurso **Pacientes** soporta CRUD y búsqueda por **RUT** (con validación de dígito verificador), **nombre** y **folio**.
- **RN-4:** El recurso **Ingresos** soporta **consulta y actualización de estado** (no se exponen operaciones fuera de §8.2 para este recurso).
- **RN-5:** El recurso **Licencias** expone **consulta de historial** y **días acumulados** por folio; el cálculo de días acumulados es el del módulo de Licencias Médicas (§7.7.3).
- **RN-6:** Solo se exponen los recursos definidos en §8.2 (Pacientes, Ingresos, Fichas clínicas, Licencias en P0; Fármacos/Controles P1; Reportes P2). No se inventan endpoints adicionales.
- **RN-7:** Toda operación de escritura/recepción se registra en el log de auditoría (consistente con OI1 y RBAC).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-121-01 | Positivo | Paciente existente | Buscar paciente por RUT vía API autenticada | RUT válido existente | `200 OK` con datos del paciente | Alta |
| TC-121-02 | Positivo (bidireccional) | Sistema externo integrado | Push de datos clínicos a Fichas clínicas y luego pull de los mismos | Payload clínico JSON | Recepción confirmada (`201/200`); datos recuperables por pull | Alta |
| TC-121-03 | Positivo (cálculo) | Folio con varias licencias | Consultar recurso Licencias del folio | Folio con N licencias | Devuelve historial completo y total de días acumulados correcto | Alta |
| TC-121-04 | Negativo | Paciente inexistente | Buscar por folio no registrado | Folio inexistente | `404 Not Found`, JSON de error | Alta |
| TC-121-05 | Borde (D12) | Integración SALUTEM activa | Procesar datos provenientes de SALUTEM | Datos clínicos origen SALUTEM | CEPA persiste localmente; **ninguna** operación de escritura hacia SALUTEM | Alta |
| TC-121-06 | Permisos | Token sin permiso sobre el recurso | Intentar actualizar estado de un Ingreso sin permiso | JWT de rol sin escritura | `403 Forbidden`; sin cambios en el ingreso | Alta |

### Definición de Hecho (DoD)
- [ ] Recursos Pacientes, Ingresos, Fichas clínicas y Licencias (P0) implementados y desplegados en QA
- [ ] Todos los CA verificados (incluyendo bidireccionalidad push/pull)
- [ ] Verificado que el aplicativo no escribe sobre SALUTEM (D12)
- [ ] Tests unitarios + integración en verde
- [ ] Endpoints documentados en OpenAPI/Swagger
- [ ] Operaciones de escritura/recepción registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Disponibilidad y naturaleza de la API del sistema de fichas clínicas (¿solo desde CEPA hacia afuera o bidireccional real?) por confirmar (PA2).
- Fármacos y Controles (P1) y Reportes (P2) se incorporarán como extensiones del mismo contrato en historias fast-follow.

---

## [CEPA-122] Integración IMED

**Épica:** EPIC-12 — API de Integración
**Perfil:** Sistema
**Prioridad (MoSCoW):** P2 Could
**Módulo PRD:** 8.3
**Trazabilidad:** PRD §8.3 (integración IMED) · PA5 (puede diferirse a futuro vía API)

### Historia
Como **sistema integrador**, quiero **recibir desde IMED datos de licencias médicas electrónicas y recetas electrónicas** para **incorporar automáticamente esa información al CEPA y evitar la digitación manual de licencias y recetas**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** un cliente IMED autenticado
  - **Cuando** envía a la API una licencia médica electrónica
  - **Entonces** el CEPA recibe y persiste la licencia vinculada al paciente/folio, confirmando con código HTTP estándar.
- **CA-2**
  - **Dado** un cliente IMED autenticado
  - **Cuando** envía una receta electrónica
  - **Entonces** el CEPA recibe y persiste la receta vinculada al folio del paciente.
- **CA-3**
  - **Dado** que la integración IMED es P2 y dependiente de PA5
  - **Cuando** se decide diferirla
  - **Entonces** la arquitectura de la API permite habilitarla a futuro sin rediseño del contrato base (v1).

### Reglas de Negocio
- **RN-1:** IMED se integra para **recepción** de licencias médicas electrónicas y recetas electrónicas (sentido entrante hacia CEPA).
- **RN-2:** La integración IMED **depende de PA5** y puede **diferirse a futuro vía API** sin bloquear el resto de la épica.
- **RN-3:** Los datos recibidos desde IMED se vinculan al folio del paciente y se registran en el log de auditoría.
- **RN-4:** La integración IMED reutiliza los principios de §8.1 (versionado, JWT, JSON, rate limiting) definidos en CEPA-120; no introduce un contrato paralelo.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-122-01 | Positivo | Cliente IMED autenticado | Enviar licencia médica electrónica | Payload IMED de licencia | `201/200`; licencia persistida y vinculada al folio | Media |
| TC-122-02 | Positivo | Cliente IMED autenticado | Enviar receta electrónica | Payload IMED de receta | `201/200`; receta persistida y vinculada al folio | Media |
| TC-122-03 | Negativo | Payload IMED mal formado | Enviar licencia sin campos obligatorios | JSON inválido | `422 Unprocessable Entity`; nada se persiste | Media |
| TC-122-04 | Permisos | Token sin scope IMED | Enviar receta con token no autorizado para IMED | JWT sin permiso | `403 Forbidden` | Media |
| TC-122-05 | No funcional (contrato OpenAPI) | Endpoints IMED publicados | Validar que los endpoints IMED figuran en la spec OpenAPI | Spec OpenAPI | Endpoints IMED documentados conforme al contrato v1 | Media |

### Definición de Hecho (DoD)
- [ ] Endpoints de recepción IMED (licencias y recetas) implementados y desplegados en QA *(si PA5 confirma alcance en v1)*
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoints documentados en OpenAPI/Swagger
- [ ] Operaciones de recepción registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- **PA5:** ¿Se requiere integración con IMED desde la v1 o se difiere como integración futura vía API? Por confirmar con Coordinación CEPA. Mientras no se resuelva, la historia se mantiene P2 y diferible.
