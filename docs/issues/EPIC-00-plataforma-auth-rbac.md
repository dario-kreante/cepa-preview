# EPIC-00 — Plataforma base, Autenticación y RBAC

**Objetivo:** Proveer la base segura del Sistema CEPA: autenticación JWT con cifrado SSL/TLS, control de acceso basado en roles (RBAC) con los 3 perfiles operativos vigentes (Coordinación, Administrativo, Auditor) y un log de auditoría inmutable que registre el 100% de las operaciones CRUD sobre datos sensibles de salud mental. Esta épica habilita el resto de los módulos funcionales (Ingresos, Fármacos, EPT, Reintegro, Auditoría, Controles, Licencias) garantizando trazabilidad y permisos diferenciados desde el inicio.

**Módulo PRD:** NFR §10 (Seguridad, Arquitectura, Autenticación JWT + RBAC) · §7.13 (Configurabilidad y Control de Acceso)
**Prioridad (MoSCoW):** P0 Must
**Alcance:**
- Inicio de sesión y gestión de sesión JWT (expiración, refresh, bloqueo por intentos fallidos).
- Cifrado SSL/TLS en tránsito; protección de datos sensibles de salud mental.
- Gestión de usuarios y roles RBAC limitada a 3 perfiles: Coordinación, Administrativo, Auditor (sin perfil Clínico, ver Decisiones v4 D1).
- Permisos diferenciados de edición vs. solo lectura por módulo; Auditor sin edición de datos clínicos.
- Log de auditoría inmutable, consultable y filtrable (quién / qué / cuándo) sobre el 100% de operaciones CRUD (objetivo institucional OI1).

**Fuera de alcance:** integración con sistemas de fichas clínicas (SALUTEM/SAM), provisionamiento de infraestructura/motor de base de datos (Oracle o PostgreSQL, ver Decisiones v4 D15), perfil Clínico (eliminado en v4 D1).

---

## [CEPA-001] Autenticación JWT e inicio de sesión

**Épica:** EPIC-00 — Plataforma base, Autenticación y RBAC
**Perfil:** Coordinación | Administrativo | Auditor (todos)
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** NFR §10 (Seguridad) · §8.1 (Autenticación basada en tokens)
**Trazabilidad:** PRD §10 (Seguridad: Cifrado SSL/TLS, Autenticación JWT) · §8.1 · §13.1 PA3 · Decisiones v4: D1, D13

### Historia
Como **usuario del Sistema CEPA (cualquier perfil)**, quiero **iniciar sesión con mis credenciales y mantener una sesión segura mediante JWT** para **acceder a la plataforma de gestión clínica protegiendo los datos sensibles de salud mental de los pacientes**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un usuario activo está en la pantalla de inicio de sesión
  - **Cuando** ingresa credenciales válidas y confirma
  - **Entonces** el sistema emite un token JWT firmado, lo entrega sobre conexión SSL/TLS y redirige al panel correspondiente a su rol.
- **CA-2**
  - **Dado** que un usuario tiene una sesión activa con JWT vigente
  - **Cuando** el token de acceso expira pero el refresh token sigue vigente
  - **Entonces** el sistema renueva la sesión de forma transparente sin solicitar credenciales nuevamente.
- **CA-3**
  - **Dado** que un usuario ingresa credenciales incorrectas de forma reiterada
  - **Cuando** alcanza el número máximo de N intentos fallidos configurado
  - **Entonces** el sistema bloquea temporalmente la cuenta y registra el evento en el log de auditoría.
- **CA-4**
  - **Dado** que un cliente intenta conectarse a la API sin cifrado o con token inválido/expirado
  - **Cuando** envía la petición
  - **Entonces** el sistema rechaza el acceso con un código HTTP de no autorizado y no expone datos.

### Reglas de Negocio
- **RN-1:** Toda sesión se gestiona mediante JWT firmado; el token de acceso tiene expiración corta y se renueva con un refresh token de vigencia mayor.
- **RN-2:** Toda comunicación cliente-servidor viaja cifrada con SSL/TLS; se rechazan peticiones no cifradas.
- **RN-3:** Tras N intentos fallidos consecutivos (parámetro configurable) la cuenta se bloquea temporalmente; el desbloqueo es por tiempo o por intervención de Coordinación.
- **RN-4:** Los datos sensibles de salud mental nunca se incluyen en el payload del JWT; el token solo porta identidad de usuario y rol.
- **RN-5:** Todo intento de inicio de sesión (éxito, fallo, bloqueo) genera traza en el log de auditoría (ver CEPA-003).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-001-01 | Positivo | Usuario activo existente | Ingresar credenciales válidas y confirmar | Usuario/clave válidos | Se emite JWT sobre SSL/TLS y se accede al panel del rol | Alta |
| TC-001-02 | Positivo | Sesión activa con access token expirado y refresh vigente | Ejecutar una acción que requiere token | Refresh token válido | El sistema renueva el JWT sin pedir credenciales | Alta |
| TC-001-03 | Negativo | Usuario activo existente | Ingresar contraseña incorrecta | Clave errónea | El sistema rechaza el acceso con mensaje genérico sin revelar el campo fallido | Alta |
| TC-001-04 | Borde | Usuario con N-1 intentos fallidos previos | Realizar un intento fallido adicional (N) | Clave errónea | La cuenta se bloquea temporalmente y se registra el evento | Alta |
| TC-001-05 | Permisos | Cliente API sin token o con token expirado | Llamar a un endpoint protegido | Token ausente/expirado | Respuesta HTTP no autorizado; no se exponen datos sensibles | Alta |
| TC-001-06 | No funcional | Endpoint de login expuesto | Conectar por canal sin cifrado (HTTP plano) | Petición no TLS | El sistema rechaza la conexión no cifrada | Media |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) de login/refresh documentados en OpenAPI/Swagger
- [ ] Operaciones de login (éxito/fallo/bloqueo) registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Valor de N (intentos máximos), tiempo de bloqueo y vigencia de tokens parametrizables; confirmar con Coordinación y TI UTalca (Mario, D13).
- PA3: confirmar requisitos institucionales adicionales de cifrado/retención para datos de salud mental.

---

## [CEPA-002] Gestión de usuarios y roles RBAC

**Épica:** EPIC-00 — Plataforma base, Autenticación y RBAC
**Perfil:** Coordinación
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** §7.13 (Control de acceso basado en roles) · NFR §10 (RBAC)
**Trazabilidad:** PRD §5.3 · §7.13 · §10 · Decisiones v4: D1

### Historia
Como **Coordinación del CEPA**, quiero **crear y administrar usuarios asignándoles uno de los 3 perfiles operativos con permisos diferenciados por módulo** para **garantizar acceso seguro y trazable a los datos sensibles, manteniendo el control pese a la alta rotación del personal**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que Coordinación está en el módulo de gestión de usuarios
  - **Cuando** crea un usuario y le asigna uno de los perfiles Coordinación, Administrativo o Auditor
  - **Entonces** el usuario queda habilitado con los permisos del perfil y aparece en el listado de usuarios.
- **CA-2**
  - **Dado** que existen 3 perfiles operativos (Coordinación, Administrativo, Auditor)
  - **Cuando** Coordinación revisa las opciones de perfil disponibles
  - **Entonces** el sistema no ofrece el perfil "Clínico" (eliminado en Decisiones v4 D1).
- **CA-3**
  - **Dado** que un usuario con perfil Auditor inicia sesión
  - **Cuando** abre un módulo con datos clínicos
  - **Entonces** el sistema permite solo lectura y bloquea cualquier acción de edición de datos clínicos.
- **CA-4**
  - **Dado** que un usuario con perfil Administrativo intenta acceder a la gestión de usuarios
  - **Cuando** solicita crear o editar un usuario
  - **Entonces** el sistema deniega la operación por falta de permisos.
- **CA-5**
  - **Dado** que un usuario deja de pertenecer al CEPA (alta rotación)
  - **Cuando** Coordinación lo desactiva
  - **Entonces** el usuario pierde el acceso inmediatamente y el cambio queda registrado en el log de auditoría.

### Reglas de Negocio
- **RN-1:** Solo existen 3 perfiles operativos: Coordinación, Administrativo y Auditor. El perfil Clínico no está disponible (Decisiones v4 D1).
- **RN-2:** Los permisos son diferenciados por módulo: edición (CRUD) vs. solo lectura, según la función del usuario.
- **RN-3:** El perfil Auditor tiene lectura total y acceso al módulo de Auditoría y reportes de cumplimiento, pero **no puede editar datos clínicos**.
- **RN-4:** El perfil Coordinación es el único habilitado para crear, editar, activar y desactivar usuarios y asignar roles.
- **RN-5:** El perfil Administrativo tiene CRUD en los módulos operativos asignados, pero no puede gestionar usuarios ni configurar roles.
- **RN-6:** La cantidad de usuarios por perfil queda abierta (alta rotación en CEPA); no hay límite fijo de cupos por perfil.
- **RN-7:** Toda alta, baja o cambio de rol de un usuario se registra en el log de auditoría (ver CEPA-003).

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-002-01 | Positivo | Sesión Coordinación | Crear usuario y asignar perfil Administrativo | Datos válidos de usuario | Usuario creado con permisos de Administrativo y visible en el listado | Alta |
| TC-002-02 | Negativo | Sesión Coordinación en alta de usuario | Intentar asignar perfil "Clínico" | Perfil Clínico | El perfil Clínico no está disponible para selección | Alta |
| TC-002-03 | Permisos | Sesión Administrativo | Intentar abrir la gestión de usuarios y crear uno | Usuario con rol Administrativo | El sistema deniega la operación por falta de permisos | Alta |
| TC-002-04 | Permisos | Sesión Auditor | Intentar editar un dato clínico en un módulo | Usuario con rol Auditor | El sistema bloquea la edición; solo permite lectura | Alta |
| TC-002-05 | Borde | Usuario activo por desvincular | Coordinación desactiva al usuario y este intenta operar | Usuario desactivado | El acceso se revoca de inmediato; el cambio queda en el log | Media |
| TC-002-06 | Positivo | Sesión Coordinación, alta rotación | Crear varios usuarios del mismo perfil | N usuarios Administrativo | Todos se crean sin límite de cupo por perfil | Media |

### Definición de Hecho (DoD)
- [ ] CRUD de usuarios y asignación de roles implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde (incluye matriz de permisos por perfil)
- [ ] Endpoint(s) de gestión de usuarios/roles documentados en OpenAPI/Swagger
- [ ] Operaciones de alta/baja/cambio de rol registradas en log de auditoría
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Matriz módulo × perfil (edición vs. solo lectura) a confirmar en detalle con Coordinación al cerrar cada módulo funcional.
- Definir si el desbloqueo de cuentas (CEPA-001 RN-3) es atribución exclusiva de Coordinación.

---

## [CEPA-003] Log de auditoría del sistema

**Épica:** EPIC-00 — Plataforma base, Autenticación y RBAC
**Perfil:** Auditor (lectura) | Coordinación (lectura)
**Prioridad (MoSCoW):** P0 Must
**Módulo PRD:** §7.13 (Log de auditoría) · NFR §10 (Seguridad)
**Trazabilidad:** PRD §7.13 · §10 · OI1 (100% de operaciones CRUD con trazabilidad) · §2.2 (control de acceso insuficiente) · Decisiones v4: D1

### Historia
Como **Auditor / Coordinación del CEPA**, quiero **consultar un log de auditoría inmutable que registre quién modificó qué dato y cuándo** para **garantizar la trazabilidad completa del 100% de las operaciones sobre datos sensibles de salud mental y verificar el cumplimiento de protocolos**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** que un usuario realiza una operación CRUD sobre cualquier registro del sistema
  - **Cuando** la operación se confirma
  - **Entonces** el sistema registra automáticamente una traza con usuario, tipo de operación, registro afectado y fecha/hora.
- **CA-2**
  - **Dado** que existe una traza en el log de auditoría
  - **Cuando** cualquier usuario (incluido un administrador) intenta modificarla o eliminarla
  - **Entonces** el sistema impide la alteración: el log es inmutable.
- **CA-3**
  - **Dado** que un Auditor o Coordinación accede al log de auditoría
  - **Cuando** aplica filtros por usuario, módulo, tipo de operación y rango de fechas
  - **Entonces** el sistema muestra las trazas que cumplen los criterios de forma consultable.
- **CA-4**
  - **Dado** que un usuario con perfil Administrativo intenta acceder al log de auditoría
  - **Cuando** solicita la vista del log
  - **Entonces** el sistema deniega el acceso por falta de permisos.

### Reglas de Negocio
- **RN-1:** El 100% de las operaciones CRUD (crear, leer-sensible, actualizar, eliminar) generan una traza con quién / qué / cuándo (objetivo institucional OI1).
- **RN-2:** Cada traza registra como mínimo: identidad del usuario, perfil/rol, tipo de operación, entidad y registro afectado, valor anterior/nuevo cuando aplica, y marca temporal.
- **RN-3:** El log es inmutable: no admite edición ni borrado por ningún perfil; solo se permite su consulta.
- **RN-4:** El log es consultable y filtrable por usuario, módulo, tipo de operación y rango de fechas.
- **RN-5:** El acceso de lectura al log se restringe a los perfiles Auditor y Coordinación; ningún otro perfil puede visualizarlo.

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-003-01 | Positivo | Usuario Administrativo registra un ingreso | Crear/actualizar un registro y confirmar | Operación CRUD válida | Se genera una traza con usuario, operación, registro y fecha/hora | Alta |
| TC-003-02 | Borde | Existe una traza en el log | Intentar editar o eliminar la traza vía UI/API | Traza existente | La operación es rechazada; la traza permanece intacta (inmutabilidad) | Alta |
| TC-003-03 | Positivo | Log con múltiples trazas | Filtrar por usuario, módulo, operación y rango de fechas | Filtros combinados | Se listan solo las trazas que cumplen los criterios | Alta |
| TC-003-04 | Permisos | Sesión Administrativo | Intentar abrir la vista del log de auditoría | Usuario con rol Administrativo | El sistema deniega el acceso al log | Alta |
| TC-003-05 | Negativo | Operación CRUD falla a mitad de transacción | Provocar fallo durante una operación | Transacción interrumpida | No queda traza parcial inconsistente; la traza solo se confirma con la operación | Media |
| TC-003-06 | Permisos | Sesión Auditor | Acceder al log y consultar trazas | Usuario con rol Auditor | El Auditor visualiza y filtra el log en modo solo lectura | Media |

### Definición de Hecho (DoD)
- [ ] Registro automático de auditoría implementado y desplegado en QA
- [ ] Todos los CA verificados (incluye verificación de cobertura del 100% de operaciones CRUD)
- [ ] Tests unitarios + integración en verde (incluye prueba de inmutabilidad)
- [ ] Endpoint(s) de consulta del log documentados en OpenAPI/Swagger
- [ ] Inmutabilidad del log verificada a nivel de aplicación y de base de datos (Oracle o PostgreSQL, ver D15)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- Definir política de retención del log conforme a normativa institucional de datos de salud mental (PA3, D13 — validación de Mario / TI UTalca).
- Confirmar si las operaciones de solo lectura sobre datos sensibles también deben dejar traza, o únicamente las de escritura.
