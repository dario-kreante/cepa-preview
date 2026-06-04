# Backlog Sistema CEPA — Épicas, Historias de Usuario y Test Cases

Backlog derivado del **PRD Sistema CEPA v1.0 (abril 2026)** + **comentarios de revisión v4**
(ver [`00-decisiones-v4.md`](./00-decisiones-v4.md)). Cada historia incluye **Criterios de
Aceptación** (Gherkin), **Reglas de Negocio** y **Test Cases**, según
[`_plantilla-historia.md`](./_plantilla-historia.md).

- **Proyecto Linear:** `CEPA - Sistema SALUTEM` (equipo Kreante / KRE)
- **Stack:** React (Vite) + TypeScript + Tailwind + shadcn/ui · NestJS · Oracle · JWT/RBAC
- **Perfiles operativos (v4):** Coordinación · Administrativo · Auditor *(el perfil Clínico no accede — usa SALUTEM)*

## Leyenda de prioridad (MoSCoW)
- **P0 Must** — bloqueante para producción.
- **P1 Should** — fast-follow post go-live.
- **P2 Could** — deseable / futuro.

## Mapa de Épicas e Historias

| Épica | Módulo PRD | Archivo |
|-------|-----------|---------|
| EPIC-00 — Plataforma base, Autenticación y RBAC | NFR §10 / §7.13 | [EPIC-00-plataforma-auth-rbac.md](./EPIC-00-plataforma-auth-rbac.md) |
| EPIC-01 — Ingresos y Gestión de Pacientes | §7.1 | [EPIC-01-ingresos.md](./EPIC-01-ingresos.md) |
| EPIC-02 — Gestión de Fármacos | §7.2 | [EPIC-02-farmacos.md](./EPIC-02-farmacos.md) |
| EPIC-03 — Seguimiento EPT | §7.3 | [EPIC-03-ept.md](./EPIC-03-ept.md) |
| EPIC-04 — Seguimiento de Reintegro | §7.4 | [EPIC-04-reintegro.md](./EPIC-04-reintegro.md) |
| EPIC-05 — Auditoría | §7.5 | [EPIC-05-auditoria.md](./EPIC-05-auditoria.md) |
| EPIC-06 — Controles Médicos | §7.6 | [EPIC-06-controles.md](./EPIC-06-controles.md) |
| EPIC-07 — Licencias Médicas | §7.7 | [EPIC-07-licencias.md](./EPIC-07-licencias.md) |
| EPIC-08 — Agendamiento Inteligente | §7.8 | [EPIC-08-agendamiento.md](./EPIC-08-agendamiento.md) |
| EPIC-09 — Reportería y Dashboard | §7.9 / §7.10 | [EPIC-09-reporteria-dashboard.md](./EPIC-09-reporteria-dashboard.md) |
| EPIC-10 — Alertas y Notificaciones | §7.11 / §7.12 | [EPIC-10-alertas-notificaciones.md](./EPIC-10-alertas-notificaciones.md) |
| EPIC-11 — Configurabilidad y Calidad de Datos | §7.13 | [EPIC-11-config-calidad.md](./EPIC-11-config-calidad.md) |
| EPIC-12 — API de Integración | §8 | [EPIC-12-api.md](./EPIC-12-api.md) |

## Índice de Historias

### EPIC-00 — Plataforma base, Autenticación y RBAC
- **CEPA-001** Autenticación JWT e inicio de sesión — P0
- **CEPA-002** Gestión de usuarios y roles (RBAC) — P0
- **CEPA-003** Log de auditoría del sistema (quién/qué/cuándo) — P0

### EPIC-01 — Ingresos y Gestión de Pacientes
- **CEPA-010** Registrar nuevo ingreso en formulario único — P0
- **CEPA-011** Folio autogenerado con opción de ingreso manual (reingresos) — P0
- **CEPA-012** Búsqueda 360° del paciente (RUT/nombre/folio) — P0
- **CEPA-013** Seguimiento del proceso clínico del ingreso — P0
- **CEPA-014** Cierre y alta del caso — P0
- **CEPA-015** Registro de ODAS y alerta de vencimiento — P0
- **CEPA-016** Validador de consentimiento informado — P0

### EPIC-02 — Gestión de Fármacos
- **CEPA-020** Registro farmacológico vinculado al folio — P0
- **CEPA-021** Historial clínico farmacológico y esquema — P0
- **CEPA-022** Gestión de recetas (emisión/revisión/envío) y alerta — P0
- **CEPA-023** Seguimiento de tratamiento (disminución/cambio de esquema) — P0

### EPIC-03 — Seguimiento EPT
- **CEPA-030** Datos del caso EPT y del empleador — P0
- **CEPA-031** Gestión del proceso EPT (plazos, testigos, entrevistas) — P0
- **CEPA-032** Plazos de informe EPT / portal ISL y alertas — P0

### EPIC-04 — Seguimiento de Reintegro
- **CEPA-040** Datos del caso de reintegro — P0
- **CEPA-041** Proceso RECA y medidas correctivas — P0
- **CEPA-042** Reintegro y cierre del caso — P0

### EPIC-05 — Auditoría
- **CEPA-050** Vista consolidada del caso (todos los hitos) — P0
- **CEPA-051** Reportes de auditoría con filtros — P0

### EPIC-06 — Controles Médicos
- **CEPA-060** Registro de control y cálculo de semana — P0
- **CEPA-061** Programación del próximo control y estado de agenda — P0
- **CEPA-062** Licencias y RECA asociadas al control — P0

### EPIC-07 — Licencias Médicas
- **CEPA-070** Registro de licencia médica — P0
- **CEPA-071** Cálculo automático de días acumulados por paciente — P0
- **CEPA-072** Alerta de vencimiento de licencia — P0
- **CEPA-073** Trazabilidad de envío a ISL y licencias extra-sistema — P0

### EPIC-08 — Agendamiento Inteligente
- **CEPA-080** Propuesta automática de agenda según disponibilidad — P1

### EPIC-09 — Reportería y Dashboard
- **CEPA-090** Dashboard multiprograma con filtros — P0
- **CEPA-091** Reportes operativos (citas/atenciones/inasistencias/anulaciones) — P0
- **CEPA-092** Reporte de cumplimiento por convenio — P0
- **CEPA-093** Reporte de carga laboral por profesional — P0
- **CEPA-094** Reporte de licencias acumuladas — P0
- **CEPA-095** Métricas de adherencia y avance de tratamiento — P1
- **CEPA-096** Ventanas de visualización por proceso — P1
- **CEPA-097** Reporte de ODAS vencidas — P0

### EPIC-10 — Alertas y Notificaciones
- **CEPA-100** Motor de alertas con plazos perentorios — P0
- **CEPA-101** Panel de notificaciones in-app por rol — P0
- **CEPA-102** Notificaciones por correo (solo alertas, SMTP) — P1
- **CEPA-103** Tareas pendientes por rol — P1

### EPIC-11 — Configurabilidad y Calidad de Datos
- **CEPA-110** Formularios dinámicos / campos configurables — P0
- **CEPA-111** Validación de parametrización y campos obligatorios — P0
- **CEPA-112** Lectura de documentos PDF — P1

### EPIC-12 — API de Integración
- **CEPA-120** API REST versionada con auth, Swagger y rate limiting — P0
- **CEPA-121** Recursos clínicos bidireccionales (push/pull con SALUTEM) — P0
- **CEPA-122** Integración IMED (recetas/licencias electrónicas) — P2
